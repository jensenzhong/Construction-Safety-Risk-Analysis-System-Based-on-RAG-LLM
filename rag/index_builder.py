import argparse
from pathlib import Path
import pandas as pd

from .config import (
    DATA_PATH,
    INDEX_DIR,
    FAISS_INDEX_PATH,
    TEXT_COL,
    ID_COL,
    KEEP_COLS,
)
from .embedding import embed_texts
from .storage import save_metadata


def clean_text_series(series: pd.Series) -> pd.Series:
    series = series.astype(str)
    series = series.str.replace(r"\s+", " ", regex=True).str.strip()
    series = series.replace({"nan": ""})
    return series


def load_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df = df.rename(columns=lambda x: x.strip())
    if TEXT_COL not in df.columns:
        raise ValueError(f"Missing column: {TEXT_COL}")
    df[ID_COL] = df.index.astype(int)
    df[TEXT_COL] = clean_text_series(df[TEXT_COL])
    df = df[df[TEXT_COL].str.len() > 0].reset_index(drop=True)
    return df


def _compose_retrieval_text(df: pd.DataFrame) -> pd.Series:
    parts = []
    if "event_keyword" in df.columns:
        parts.append(clean_text_series(df["event_keyword"]))
    if "event_type" in df.columns:
        parts.append(clean_text_series(df["event_type"]))
    parts.append(clean_text_series(df[TEXT_COL]))
    if "description" in df.columns:
        parts.append(clean_text_series(df["description"]))

    joined = pd.Series([""] * len(df), index=df.index, dtype="object")
    for col in parts:
        joined = joined.str.cat(col, sep=" ")
    return clean_text_series(joined)


def build_index(csv_path: Path = DATA_PATH, device: str = "cpu") -> Path:
    import faiss  # local import to allow dependency check

    df = load_data(csv_path)
    texts = _compose_retrieval_text(df).tolist()

    vectors = embed_texts(texts, device=device)
    dim = vectors.shape[1]

    index = faiss.IndexFlatIP(dim)
    index.add(vectors)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(FAISS_INDEX_PATH))

    keep_cols = [c for c in KEEP_COLS if c in df.columns]
    metadata = df[keep_cols].copy()
    save_metadata(metadata)

    return FAISS_INDEX_PATH


def main():
    parser = argparse.ArgumentParser(description="Build FAISS index for CSDataset")
    parser.add_argument("--csv", default=str(DATA_PATH), help="Path to Injury Severity.CSV")
    parser.add_argument("--device", default="cpu", help="Embedding device: cpu or cuda")
    args = parser.parse_args()

    index_path = build_index(Path(args.csv), device=args.device)
    print(f"Index written to: {index_path}")


if __name__ == "__main__":
    main()
