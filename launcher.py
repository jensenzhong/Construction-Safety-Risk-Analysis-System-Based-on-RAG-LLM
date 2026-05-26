from __future__ import annotations

import ctypes
import os
import shutil
import sys
import threading
import traceback
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from streamlit.web import cli as stcli


APP_URL = "http://127.0.0.1:8501"
HEALTHCHECK_URL = f"{APP_URL}/_stcore/health"
APP_NAME = "ConstructionSafetyAssistant"


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS")).resolve()
    return Path(__file__).resolve().parent


def _app_home() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_NAME / "Data"
    return Path.home() / APP_NAME / "Data"


def _launcher_log_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        base_dir = Path(local_app_data) / APP_NAME
    else:
        base_dir = Path.home() / APP_NAME
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "launcher.log"


def _append_log(message: str) -> None:
    log_path = _launcher_log_path()
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(message)
        if not message.endswith("\n"):
            handle.write("\n")


def _show_error_dialog(message: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, message, APP_NAME, 0x10)
    except Exception:
        pass


def _copy_seed(src: Path, dst: Path) -> None:
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst)
    elif src.exists():
        shutil.copy2(src, dst)


def _copy_seed_dir_contents(src: Path, dst: Path) -> None:
    """Copy missing files from src directory into dst directory.

    Unlike _copy_seed, this function inspects individual files inside
    a directory so that a partially-populated destination is repaired
    rather than silently skipped.
    """
    if not src.is_dir():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        dst_item = dst / item.name
        if not dst_item.exists():
            if item.is_dir():
                shutil.copytree(item, dst_item)
            else:
                shutil.copy2(item, dst_item)


def _prepare_runtime_tree(bundle_root: Path, app_home: Path) -> None:
    _copy_seed(bundle_root / "Injury Severity.CSV", app_home / "Injury Severity.CSV")
    # Use file-level check so a directory that exists but is missing
    # faiss.index (or other artefacts) gets repaired on next launch.
    _copy_seed_dir_contents(bundle_root / "indexes", app_home / "indexes")
    _copy_seed(bundle_root / "README_START.txt", app_home / "README_START.txt")
    _copy_seed(bundle_root / "settings.json", app_home / "settings.json")
    _copy_seed(bundle_root / ".env", app_home / ".env")


def _resolve_writable_app_home(bundle_root: Path) -> Path:
    candidates = [
        _app_home(),
        bundle_root / ".runtime_appdata" / "Data",
        Path.cwd() / ".runtime_appdata" / "Data",
    ]
    last_error = None
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return candidate
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"No writable app data directory is available: {last_error}")


def _configure_env(app_home: Path) -> None:
    profile_home = app_home / ".streamlit_local"
    config_dir = profile_home / ".streamlit"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.toml").write_text(
        "[global]\n"
        "developmentMode = false\n\n"
        "[browser]\n"
        "gatherUsageStats = false\n\n"
        "[server]\n"
        "headless = true\n",
        encoding="utf-8",
    )
    os.environ["CSDATASET_HOME"] = str(app_home)
    os.environ["USERPROFILE"] = str(profile_home)
    os.environ["HOME"] = str(profile_home)


def _ensure_bundle_on_path(bundle_root: Path) -> None:
    bundle_str = str(bundle_root)
    if bundle_str not in sys.path:
        sys.path.insert(0, bundle_str)
    existing = os.environ.get("PYTHONPATH", "")
    if existing:
        if bundle_str not in existing.split(os.pathsep):
            os.environ["PYTHONPATH"] = bundle_str + os.pathsep + existing
    else:
        os.environ["PYTHONPATH"] = bundle_str


def _redirect_output_to_log() -> None:
    log_handle = _launcher_log_path().open("a", encoding="utf-8", buffering=1)
    sys.stdout = log_handle
    sys.stderr = log_handle


def _open_browser_later() -> None:
    if os.getenv("CSDATASET_NO_BROWSER") == "1":
        return
    timer = threading.Timer(2.0, lambda: webbrowser.open(APP_URL))
    timer.daemon = True
    timer.start()


def _open_browser_now() -> None:
    if os.getenv("CSDATASET_NO_BROWSER") == "1":
        return
    webbrowser.open(APP_URL)


def _is_existing_instance_running() -> bool:
    try:
        with urllib.request.urlopen(HEALTHCHECK_URL, timeout=1.5) as response:
            body = response.read(64).decode("utf-8", errors="ignore").strip().lower()
            return response.status == 200 and "ok" in body
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False


def main() -> int:
    bundle_root = _bundle_root()
    _redirect_output_to_log()
    _append_log(f"[START] Launching app from {bundle_root}")
    if _is_existing_instance_running():
        _append_log(f"[INFO] Existing app instance is already serving at {APP_URL}")
        _open_browser_now()
        return 0

    app_home = _resolve_writable_app_home(bundle_root)
    _append_log(f"[START] Using app data directory {app_home}")
    _ensure_bundle_on_path(bundle_root)
    _prepare_runtime_tree(bundle_root=bundle_root, app_home=app_home)
    _configure_env(app_home=app_home)
    _open_browser_later()

    sys.argv = [
        "streamlit",
        "run",
        str(bundle_root / "app.py"),
        "--global.developmentMode",
        "false",
        "--server.address",
        "127.0.0.1",
        "--server.port",
        "8501",
    ]
    return stcli.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        details = traceback.format_exc()
        _append_log(details)
        _show_error_dialog(
            "The application failed to start.\n\n"
            f"Please check the log file:\n{_launcher_log_path()}"
        )
        raise
