from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import time
import traceback
import zipfile
from pathlib import Path


APP_NAME = "Construction Safety Assistant"
APP_ID = "ConstructionSafetyAssistant"
PAYLOAD_ZIP = "ConstructionSafetyAssistant.zip"
APP_EXE_NAME = "ConstructionSafetyAssistant.exe"


def _install_base() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_ID
    return Path.home() / APP_ID


def _desktop_shortcut() -> Path:
    return Path.home() / "Desktop" / f"{APP_NAME}.lnk"


def _start_menu_dir() -> Path:
    app_data = os.environ.get("APPDATA")
    if app_data:
        return Path(app_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / APP_NAME
    return Path.home() / APP_NAME


def _resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS")).resolve()
    return Path(__file__).resolve().parent


def _payload_zip_path() -> Path:
    return _resource_root() / PAYLOAD_ZIP


def _installer_log_path() -> Path:
    path = _install_base() / "installer.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _append_log(message: str) -> None:
    with _installer_log_path().open("a", encoding="utf-8") as handle:
        handle.write(message)
        if not message.endswith("\n"):
            handle.write("\n")


def _show_error_dialog(message: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, message, APP_NAME, 0x10)
    except Exception:
        pass


def _show_info_dialog(message: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, message, APP_NAME, 0x40)
    except Exception:
        pass


def _is_app_running() -> bool:
    """Check if the application is currently running."""
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                f"Get-Process -Name '{APP_EXE_NAME.replace('.exe', '')}' -ErrorAction SilentlyContinue",
            ],
            capture_output=True,
            text=True,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def _terminate_app() -> bool:
    """Attempt to terminate the running application. Returns True if successful."""
    try:
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                f"Stop-Process -Name '{APP_EXE_NAME.replace('.exe', '')}' -Force -ErrorAction SilentlyContinue",
            ],
            check=True,
        )
        # Wait for process to fully terminate
        for _ in range(10):
            if not _is_app_running():
                return True
            time.sleep(0.5)
        return not _is_app_running()
    except Exception:
        return False


def _safe_rmtree(path: Path, max_retries: int = 3) -> bool:
    """Safely remove directory tree with retries. Returns True if successful."""
    for attempt in range(max_retries):
        try:
            if path.exists():
                shutil.rmtree(path)
            return True
        except PermissionError:
            if attempt < max_retries - 1:
                time.sleep(1)
                # Try to terminate app again if files are locked
                _terminate_app()
            continue
        except Exception:
            return False
    return False


def _escape_ps(value: str) -> str:
    return value.replace("'", "''")


def _run_powershell(script: str) -> None:
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        check=True,
    )


def _create_shortcuts(target_exe: Path) -> None:
    desktop_shortcut = _desktop_shortcut()
    start_menu_dir = _start_menu_dir()
    start_menu_dir.mkdir(parents=True, exist_ok=True)
    start_menu_shortcut = start_menu_dir / f"{APP_NAME}.lnk"

    script = (
        "$shell=New-Object -ComObject WScript.Shell; "
        f"$desktop=$shell.CreateShortcut('{_escape_ps(str(desktop_shortcut))}'); "
        f"$desktop.TargetPath='{_escape_ps(str(target_exe))}'; "
        f"$desktop.WorkingDirectory='{_escape_ps(str(target_exe.parent))}'; "
        f"$desktop.IconLocation='{_escape_ps(str(target_exe))},0'; "
        "$desktop.Save(); "
        f"$menu=$shell.CreateShortcut('{_escape_ps(str(start_menu_shortcut))}'); "
        f"$menu.TargetPath='{_escape_ps(str(target_exe))}'; "
        f"$menu.WorkingDirectory='{_escape_ps(str(target_exe.parent))}'; "
        f"$menu.IconLocation='{_escape_ps(str(target_exe))},0'; "
        "$menu.Save()"
    )
    _run_powershell(script)


def _install_payload() -> Path:
    install_base = _install_base()
    install_dir = install_base / "App"
    start_menu_dir = _start_menu_dir()
    staging_root = install_base / ".staging"
    backup_dir: Path | None = None

    # Check if app is running and attempt to close it
    if _is_app_running():
        _append_log("[INFO] Application is running, attempting to close...")
        if not _terminate_app():
            _show_error_dialog(
                f"{APP_NAME} is currently running and cannot be closed automatically.\n\n"
                "Please close the application manually and run the installer again."
            )
            raise RuntimeError("Application is running and cannot be terminated")
        _append_log("[INFO] Application closed successfully")

    install_base.mkdir(parents=True, exist_ok=True)
    if staging_root.exists() and not _safe_rmtree(staging_root):
        raise RuntimeError(f"Cannot clear staging directory: {staging_root}")
    staging_root.mkdir(parents=True, exist_ok=True)

    # Extract payload into staging first so a failed update does not corrupt an existing install.
    with zipfile.ZipFile(_payload_zip_path()) as archive:
        archive.extractall(staging_root)

    staged_install_dir = staging_root / "App"
    staged_exe = staged_install_dir / APP_EXE_NAME
    if not staged_exe.exists():
        raise FileNotFoundError(f"Installer payload did not contain {staged_exe}")

    # Move existing install out of the way (avoid partial deletion if files are locked).
    if install_dir.exists():
        suffix = str(int(time.time()))
        candidate = install_base / f"App.backup.{suffix}"
        counter = 0
        while candidate.exists():
            counter += 1
            candidate = install_base / f"App.backup.{suffix}.{counter}"
        try:
            install_dir.rename(candidate)
            backup_dir = candidate
        except Exception:
            _show_error_dialog(
                f"Cannot update the installation directory.\n\n"
                "Please make sure the application is fully closed "
                "(check Task Manager) and try again."
            )
            raise

    # Remove old Start Menu shortcuts (best-effort).
    if start_menu_dir.exists() and not _safe_rmtree(start_menu_dir):
        _append_log(f"[WARN] Cannot remove start menu directory: {start_menu_dir}")

    try:
        staged_install_dir.rename(install_dir)
    except Exception:
        if backup_dir:
            try:
                backup_dir.rename(install_dir)
                backup_dir = None
                _append_log("[INFO] Restored previous installation after failed update")
            except Exception:
                _append_log("[ERROR] Failed to restore previous installation after failed update")
        raise

    if staging_root.exists() and not _safe_rmtree(staging_root):
        _append_log(f"[WARN] Cannot remove staging directory: {staging_root}")

    # Best-effort cleanup of the previous version.
    if backup_dir and not _safe_rmtree(backup_dir):
        _append_log(f"[WARN] Cannot remove old installation directory: {backup_dir}")

    target_exe = install_dir / APP_EXE_NAME
    if not target_exe.exists():
        raise FileNotFoundError(f"Installer payload did not contain {target_exe}")

    _create_shortcuts(target_exe)
    return target_exe


def main() -> int:
    _append_log("[START] Running installer")
    target_exe = _install_payload()
    _append_log(f"[DONE] Installed app to {target_exe.parent}")
    subprocess.Popen([str(target_exe)], cwd=target_exe.parent)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        details = traceback.format_exc()
        _append_log(details)
        _show_error_dialog(
            "Installation failed.\n\n"
            f"Please check the log file:\n{_installer_log_path()}"
        )
        raise
