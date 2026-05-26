from pathlib import Path
import pandas as pd

from .config import INDEX_DIR, METADATA_PATH, METADATA_JSONL_PATH


def save_metadata(df: pd.DataFrame) -> Path:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    try:
        df.to_parquet(METADATA_PATH, index=False)
        return METADATA_PATH
    except Exception:
        df.to_json(METADATA_JSONL_PATH, orient="records", lines=True)
        return METADATA_JSONL_PATH


def load_metadata() -> pd.DataFrame:
    if METADATA_PATH.exists():
        try:
            return pd.read_parquet(METADATA_PATH)
        except Exception:
            if METADATA_JSONL_PATH.exists():
                return pd.read_json(METADATA_JSONL_PATH, lines=True)
            raise
    if METADATA_JSONL_PATH.exists():
        return pd.read_json(METADATA_JSONL_PATH, lines=True)
    raise FileNotFoundError("metadata.parquet or metadata.jsonl not found")
