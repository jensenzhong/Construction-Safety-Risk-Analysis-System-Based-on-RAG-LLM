import numpy as np
from pathlib import Path
import os
from hashlib import blake2b

from .config import EMBED_MODEL, BATCH_SIZE, HASHING_DIM

_model = None
_model_device = None
_vectorizer = None


def _init_hashing():
    global _vectorizer
    if _vectorizer is None:
        try:
            from sklearn.feature_extraction.text import HashingVectorizer

            _vectorizer = HashingVectorizer(
                n_features=HASHING_DIM,
                alternate_sign=False,
                norm=None,
            )
        except Exception:
            _vectorizer = "simple_hash"
    return _vectorizer


def get_model(device: str = "cpu"):
    global _model, _model_device
    if _model is None or _model_device != device:
        try:
            from sentence_transformers import SentenceTransformer

            is_local_path = Path(EMBED_MODEL).exists()
            force_local_only = os.getenv("HF_HUB_OFFLINE", "0") == "1" or is_local_path
            _model = SentenceTransformer(
                EMBED_MODEL,
                device=device,
                local_files_only=force_local_only,
            )
            _model_device = device
        except Exception as exc:  # fallback to hashing vectorizer
            _model = None
            _model_device = "hashing"
            _init_hashing()
            print(f"[warn] SentenceTransformer unavailable, using hashing embeddings: {exc}")
    return _model


def _simple_hash_embeddings(texts) -> np.ndarray:
    vectors = np.zeros((len(texts), HASHING_DIM), dtype="float32")
    for i, text in enumerate(texts):
        for token in str(text).lower().split():
            idx = int.from_bytes(blake2b(token.encode("utf-8"), digest_size=8).digest(), "little") % HASHING_DIM
            vectors[i, idx] += 1.0
    norms = np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-12
    return vectors / norms


def _hashing_embeddings(texts) -> np.ndarray:
    vectorizer = _init_hashing()
    if vectorizer == "simple_hash":
        return _simple_hash_embeddings(texts)
    mat = vectorizer.transform(texts)
    vectors = mat.toarray().astype("float32")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-12
    return vectors / norms


def embed_texts(texts, device: str = "cpu", batch_size: int = BATCH_SIZE) -> np.ndarray:
    model = get_model(device=device)
    if model is None or _model_device == "hashing":
        return _hashing_embeddings(texts)

    try:
        vectors = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
    except TypeError:
        vectors = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
        )
        norms = np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-12
        vectors = vectors / norms

    if vectors.dtype != np.float32:
        vectors = vectors.astype("float32")
    return vectors
