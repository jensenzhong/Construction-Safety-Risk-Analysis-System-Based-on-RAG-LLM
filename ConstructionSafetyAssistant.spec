# -*- mode: python ; coding: utf-8 -*-

import json
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all


project_root = Path.cwd()
datas = [
    (str(project_root / "app.py"), "."),
    (str(project_root / "Injury Severity.CSV"), "."),
    (str(project_root / "README_START.txt"), "."),
    (str(project_root / "indexes"), "indexes"),
    (str(project_root / "llm"), "llm"),
    (str(project_root / "rag"), "rag"),
    (str(project_root / "sensors"), "sensors"),
]

for optional_config in ("settings.json", ".env"):
    config_path = project_root / optional_config
    if config_path.exists():
        datas.append((str(config_path), "."))

if not any((project_root / name).exists() for name in ("settings.json", ".env")):
    deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if deepseek_api_key:
        generated_config_dir = project_root / "build" / "bundle_config"
        generated_config_dir.mkdir(parents=True, exist_ok=True)
        generated_config_path = generated_config_dir / "settings.json"
        generated_config_path.write_text(
            json.dumps(
                {
                    "deepseek": {
                        "api_key": deepseek_api_key,
                        "base_url": os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").strip()
                        or "https://api.deepseek.com/v1",
                        "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat",
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        datas.append((str(generated_config_path), "."))

binaries = []
hiddenimports = []

for package_name in [
    "streamlit",
    "plotly",
    "pyarrow",
    "faiss",
    "altair",
    "tornado",
    "setuptools",
]:
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(package_name)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports


a = Analysis(
    ["launcher.py"],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ConstructionSafetyAssistant",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ConstructionSafetyAssistant",
)
