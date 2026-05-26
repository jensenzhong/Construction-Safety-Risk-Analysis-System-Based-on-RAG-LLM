from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS_FILE = ROOT / "requirements.txt"
INDEX_DIR = ROOT / "indexes"
RUNTIME_SITE = ROOT / ".runtime_packages"
LOCAL_PROFILE = ROOT / ".streamlit_local"
PIP_CACHE_DIR = ROOT / ".pip_cache"
APP_URL = "http://127.0.0.1:8501"
HEALTHCHECK_URL = f"{APP_URL}/_stcore/health"

REQUIRED_MODULES = {
    "streamlit": "streamlit",
    "plotly": "plotly",
    "pandas": "pandas",
    "numpy": "numpy",
    "openai": "openai",
    "scikit-learn": "sklearn",
    "faiss-cpu": "faiss",
    "sentence-transformers": "sentence_transformers",
    "pyarrow": "pyarrow",
}


def _print(message: str) -> None:
    print(message, flush=True)


def _runtime_env() -> dict:
    env = os.environ.copy()
    python_path_parts = [str(RUNTIME_SITE)]
    if env.get("PYTHONPATH"):
        python_path_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(python_path_parts)
    env["PYTHONNOUSERSITE"] = "1"
    env["PIP_CACHE_DIR"] = str(PIP_CACHE_DIR)
    env["USERPROFILE"] = str(LOCAL_PROFILE)
    env["HOME"] = str(LOCAL_PROFILE)
    return env


def _load_runtime_site() -> None:
    runtime_site_str = str(RUNTIME_SITE)
    if runtime_site_str not in sys.path:
        sys.path.insert(0, runtime_site_str)


def _missing_modules() -> list[str]:
    _load_runtime_site()
    missing = []
    for package_name, module_name in REQUIRED_MODULES.items():
        if importlib.util.find_spec(module_name) is None:
            missing.append(package_name)
    return missing


def _run(args: list[str], env: dict) -> None:
    subprocess.run(args, cwd=ROOT, env=env, check=True)


def _ensure_pip(env: dict) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pip", "--version"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode == 0:
        return
    _print("[SETUP] pip is missing. Installing pip...")
    _run([sys.executable, "-m", "ensurepip", "--upgrade"], env)


def _install_requirements(env: dict) -> None:
    RUNTIME_SITE.mkdir(parents=True, exist_ok=True)
    PIP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _print("[SETUP] Installing Python dependencies into the project folder...")
    _run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--upgrade",
            "--target",
            str(RUNTIME_SITE),
            "-r",
            str(REQUIREMENTS_FILE),
        ],
        env,
    )


def _ensure_index(env: dict) -> None:
    has_faiss = (INDEX_DIR / "faiss.index").exists()
    has_metadata = (INDEX_DIR / "metadata.parquet").exists() or (INDEX_DIR / "metadata.jsonl").exists()
    if has_faiss and has_metadata:
        return
    _print("[SETUP] Building retrieval index...")
    _run([sys.executable, "-m", "rag.index_builder", "--device", "cpu"], env)


def _write_streamlit_config() -> None:
    config_dir = LOCAL_PROFILE / ".streamlit"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.toml").write_text(
        "[browser]\n"
        "gatherUsageStats = false\n\n"
        "[server]\n"
        "headless = true\n",
        encoding="utf-8",
    )


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
    env = _runtime_env()
    _write_streamlit_config()
    _ensure_pip(env)

    missing = _missing_modules()
    if missing:
        _print(f"[SETUP] Missing packages: {', '.join(missing)}")
        _install_requirements(env)
        missing = _missing_modules()
        if missing:
            _print(f"[ERROR] Packages are still missing after installation: {', '.join(missing)}")
            return 1
    else:
        _print("[SETUP] All required packages are available.")

    if _is_existing_instance_running():
        _print(f"[START] Existing app instance detected at {APP_URL}. Opening browser...")
        _open_browser_now()
        return 0

    _ensure_index(env)
    _print(f"[START] Opening Streamlit app at {APP_URL}")
    _open_browser_later()
    _run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app.py",
            "--server.address",
            "127.0.0.1",
            "--server.port",
            "8501",
        ],
        env,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
