import os
import sys
from pathlib import Path


def _resolve_base_dir() -> Path:
    env_dir = os.getenv("CSDATASET_HOME")
    if env_dir:
        return Path(env_dir).expanduser().resolve()

    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            return Path(meipass).resolve()
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent.parent


BASE_DIR = _resolve_base_dir()

DATA_PATH = BASE_DIR / "Injury Severity.CSV"
INDEX_DIR = BASE_DIR / "indexes"
FAISS_INDEX_PATH = INDEX_DIR / "faiss.index"
METADATA_PATH = INDEX_DIR / "metadata.parquet"
METADATA_JSONL_PATH = INDEX_DIR / "metadata.jsonl"


def _resolve_embed_model() -> str:
    env_model = os.getenv("EMBED_MODEL_PATH")
    if env_model:
        return env_model

    local_model_root = Path.home() / ".cache" / "sentence_transformers"
    local_candidates = [
        local_model_root / "all-MiniLM-L6-v2",
        local_model_root / "all-minilm-l6-v2",
    ]

    for candidate in local_candidates:
        if candidate.exists():
            return str(candidate)

    return "sentence-transformers/all-MiniLM-L6-v2"


EMBED_MODEL = _resolve_embed_model()
TEXT_COL = "abstract"
ID_COL = "case_id"

KEEP_COLS = [
    "case_id",
    "abstract",
    "event_keyword",
    "degree_of_inj_x",
    "date",
    "state_x",
    "city_x",
    "temp",
    "wind_speed",
    "wind_deg",
]

BATCH_SIZE = 128
HASHING_DIM = 384
