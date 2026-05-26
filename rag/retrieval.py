import re
from typing import Dict, List, Set

from .config import FAISS_INDEX_PATH
from .embedding import embed_texts
from .storage import load_metadata

ZH_TO_EN_HINTS = {
    "高处": "work at height",
    "坠落": "fall",
    "触电": "electric shock",
    "电弧": "arc flash",
    "脚手架": "scaffold",
    "梯子": "ladder",
    "吊装": "lifting operation",
    "起重": "crane",
    "机械": "machinery",
    "卷入": "caught-in",
    "车辆": "vehicle",
    "叉车": "forklift",
    "挖沟": "trench excavation",
    "坍塌": "collapse",
    "焊接": "welding",
    "热作": "hot work",
    "火灾": "fire",
    "爆炸": "explosion",
    "中毒": "toxic exposure",
    "缺氧": "oxygen deficiency",
    "临边": "open edge",
    "安全带": "safety harness",
    "风大": "strong wind",
}

_WORD_RE = re.compile(r"[a-z0-9]+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
_EN_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
    "on",
    "at",
    "with",
    "for",
    "from",
    "by",
    "is",
    "are",
    "was",
    "were",
}


def load_index():
    import faiss

    if not FAISS_INDEX_PATH.exists():
        raise FileNotFoundError("FAISS index not found. Build it first.")
    return faiss.read_index(str(FAISS_INDEX_PATH))


def _expand_query(query: str) -> str:
    text = str(query)
    hints = sorted({en for zh, en in ZH_TO_EN_HINTS.items() if zh in text})
    if not hints:
        return text
    return f"{text}\n\nPotential English keywords: {'; '.join(hints)}"


def _tokenize(text: str) -> Set[str]:
    content = str(text).lower()
    tokens = {tok for tok in _WORD_RE.findall(content) if tok not in _EN_STOPWORDS}
    for chunk in _CJK_RE.findall(str(text)):
        chars = [c for c in chunk if c.strip()]
        if len(chars) == 1:
            tokens.add(chars[0])
            continue
        for i in range(len(chars) - 1):
            tokens.add("".join(chars[i : i + 2]))
    return tokens


def _keyword_overlap_score(query: str, case_text: str) -> float:
    q_tokens = _tokenize(query)
    if not q_tokens:
        return 0.0
    c_tokens = _tokenize(case_text)
    if not c_tokens:
        return 0.0
    overlap = len(q_tokens & c_tokens)
    # Normalize by query length so longer query does not dominate.
    return min(1.0, overlap / max(1, min(len(q_tokens), 10)))


def retrieve(query: str, top_k: int = 3, device: str = "cpu") -> List[Dict]:
    index = load_index()
    metadata = load_metadata()
    if metadata.empty:
        return []

    expanded_query = _expand_query(query)
    query_vec = embed_texts([expanded_query], device=device)
    if query_vec.shape[1] != index.d:
        raise RuntimeError(
            f"Embedding dimension mismatch: query={query_vec.shape[1]} index={index.d}. "
            "Rebuild index in the same runtime environment."
        )

    search_k = min(max(top_k, top_k * 8), len(metadata))
    scores, indices = index.search(query_vec, search_k)

    results: List[Dict] = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        row = metadata.iloc[int(idx)].to_dict()
        semantic_score = float(score)
        case_text = f"{row.get('event_keyword', '')} {row.get('abstract', '')}"
        keyword_score = _keyword_overlap_score(expanded_query, case_text)
        # Hybrid ranking: semantic score as primary, keyword overlap as tie-breaker.
        row["score"] = semantic_score
        row["keyword_score"] = round(keyword_score, 4)
        row["hybrid_score"] = float(0.85 * semantic_score + 0.15 * keyword_score)
        results.append(row)

    results.sort(key=lambda item: item.get("hybrid_score", item.get("score", 0.0)), reverse=True)
    return results[:top_k]
