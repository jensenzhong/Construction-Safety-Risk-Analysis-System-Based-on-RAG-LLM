from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT / "build"
DIST_DIR = ROOT / "dist"
RELEASE_DIR = ROOT / "release"
PAYLOAD_ROOT = BUILD_DIR / "installer_payload"
ZIP_STAGING_DIR = BUILD_DIR / "zip_staging"
APP_DIST_DIR = DIST_DIR / "ConstructionSafetyAssistant"
APP_INSTALL_DIR = ZIP_STAGING_DIR / "App"
ZIP_BASE = PAYLOAD_ROOT / "ConstructionSafetyAssistant"
ZIP_FILE = PAYLOAD_ROOT / "ConstructionSafetyAssistant.zip"
INSTALLER_SCRIPT = ROOT / "scripts" / "installer_bootstrap.py"
INSTALLER_BUILD_DIR = BUILD_DIR / "installer_bootstrap"
INSTALLER_EXE = RELEASE_DIR / "ConstructionSafetyAssistant-Installer.exe"
INDEX_PARQUET = ROOT / "indexes" / "metadata.parquet"
INDEX_JSONL = ROOT / "indexes" / "metadata.jsonl"


def run(args: list[str]) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def ensure_metadata_jsonl() -> None:
    if INDEX_JSONL.exists() or not INDEX_PARQUET.exists():
        return
    df = pd.read_parquet(INDEX_PARQUET)
    df.to_json(INDEX_JSONL, orient="records", lines=True, force_ascii=False)


def build_pyinstaller_app() -> None:
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "ConstructionSafetyAssistant.spec",
        ]
    )


def build_zip_payload() -> None:
    clean_dir(PAYLOAD_ROOT)
    clean_dir(ZIP_STAGING_DIR)
    shutil.copytree(APP_DIST_DIR, APP_INSTALL_DIR, dirs_exist_ok=True)
    archive_path = shutil.make_archive(str(ZIP_BASE), "zip", root_dir=ZIP_STAGING_DIR)
    if Path(archive_path) != ZIP_FILE:
        shutil.copy2(archive_path, ZIP_FILE)


def build_installer_exe() -> None:
    clean_dir(INSTALLER_BUILD_DIR)
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    data_arg = f"{ZIP_FILE};."
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--windowed",
            "--name",
            "ConstructionSafetyAssistant-Installer",
            "--distpath",
            str(RELEASE_DIR),
            "--workpath",
            str(INSTALLER_BUILD_DIR),
            "--specpath",
            str(BUILD_DIR),
            "--add-data",
            data_arg,
            str(INSTALLER_SCRIPT),
        ]
    )


def main() -> int:
    ensure_metadata_jsonl()
    build_pyinstaller_app()
    build_zip_payload()
    build_installer_exe()
    print(f"Installer created at: {INSTALLER_EXE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
