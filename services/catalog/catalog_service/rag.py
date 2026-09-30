"""Product-knowledge retrieval (ChromaDB + sentence-transformers).

The index is read-only at runtime and deterministic from ``data/product_docs``.
It is built at image build time (``scripts/ingest_knowledge.py``) or on first
start when missing (``RAG_BUILD_ON_START``). When chromadb, the embedding model
or the index is unavailable, :func:`search` returns ``available: false``
instead of raising.

Environment:

* ``CHROMA_PATH``           persistent Chroma directory (default ``services/catalog/data/embeddings``)
* ``EMBEDDING_MODEL_PATH``  local sentence-transformers model directory (optional);
                            falls back to ``EMBEDDING_MODEL`` (default ``all-MiniLM-L6-v2``)
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import threading
from pathlib import Path
from typing import Any, Optional, Protocol, Sequence

from .models import KnowledgePassage, KnowledgeResult

logger = logging.getLogger("catalog_service.rag")

SERVICE_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = SERVICE_ROOT / "data" / "product_docs"
DEFAULT_CHROMA_PATH = SERVICE_ROOT / "data" / "embeddings"
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "product_knowledge"

#: Source document stem -> metadata attached to each chunk.
DOC_METADATA: dict[str, dict[str, str]] = {
    "fiber_internet": {"product_family": "fiber", "product_ids": "FIB-1G,FIB-5G,FIB-10G"},
    "coax_internet": {"product_family": "coax", "product_ids": "COAX-200M,COAX-500M,COAX-1G"},
    "voice_services": {
        "product_family": "voice",
        "product_ids": "VOICE-BAS,VOICE-STD,VOICE-ENT,VOICE-UCAAS",
    },
    "sd_wan": {"product_family": "sd-wan", "product_ids": "SDWAN-ESS,SDWAN-PRO,SDWAN-ENT"},
    "mobile_services": {"product_family": "mobile", "product_ids": "MOB-BAS,MOB-UNL,MOB-PREM"},
}


class Embedder(Protocol):
    def encode(self, texts: Sequence[str]) -> list[list[float]]: ...


class RagUnavailable(RuntimeError):
    """The knowledge index cannot be used (missing deps, model or index)."""


def chroma_path() -> Path:
    return Path(os.getenv("CHROMA_PATH", "").strip() or DEFAULT_CHROMA_PATH)


def embedding_model_name() -> str:
    local = os.getenv("EMBEDDING_MODEL_PATH", "").strip()
    if local and Path(local).is_dir():
        return local
    return os.getenv("EMBEDDING_MODEL", "").strip() or DEFAULT_EMBEDDING_MODEL


class SentenceTransformerEmbedder:
    def __init__(self, model: Optional[str] = None) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RagUnavailable("sentence-transformers is not installed") from exc
        name = model or embedding_model_name()
        try:
            self._model = SentenceTransformer(name)
        except Exception as exc:  # model download / load failure
            raise RagUnavailable(f"embedding model {name!r} could not be loaded: {exc}") from exc

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        return self._model.encode(list(texts), show_progress_bar=False).tolist()


# ---------------------------------------------------------------------------
# Chunking (moved from the ProductAgent ingestion script)
# ---------------------------------------------------------------------------

_HEADING = re.compile(r"^(#{2,3})\s+(.+)$", re.MULTILINE)


def _split_by_headings(text: str, filename: str) -> list[dict]:
    positions = [(m.start(), m.group(2).strip()) for m in _HEADING.finditer(text)]
    if not positions:
        stripped = text.strip()
        return [{"text": stripped, "section": filename}] if stripped else []
    chunks = []
    preamble = text[: positions[0][0]].strip()
    if preamble:
        chunks.append({"text": preamble, "section": "Overview"})
    for i, (pos, heading) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        chunk = text[pos:end].strip()
        if chunk:
            chunks.append({"text": chunk, "section": heading})
    return chunks


def _split_long(text: str, section: str, max_chars: int = 1800, overlap: int = 150) -> list[dict]:
    if len(text) <= max_chars:
        return [{"text": text, "section": section}]
    out, current = [], ""
    for para in re.split(r"\n{2,}", text):
        if len(current) + len(para) + 2 > max_chars and current:
            out.append({"text": current.strip(), "section": section})
            current = current[-overlap:].lstrip() + "\n\n" + para
        else:
            current = current + ("\n\n" if current else "") + para
    if current.strip():
        out.append({"text": current.strip(), "section": section})
    return out


def chunk_document(path: Path) -> list[dict]:
    """Split a markdown document on H2/H3 headings, then split long sections."""
    chunks = []
    for section in _split_by_headings(path.read_text(encoding="utf-8"), path.stem):
        chunks.extend(_split_long(section["text"], section["section"]))
    return chunks


def _stable_id(filename: str, index: int) -> str:
    return "prod_" + hashlib.sha256(f"{filename}::chunk_{index:04d}".encode()).hexdigest()[:16]


def iter_chunks(docs_dir: Path = DOCS_DIR):
    """Yield ``(id, text, metadata)`` for every chunk of every product document."""
    for doc in sorted(docs_dir.glob("*.md")):
        if doc.stem.upper() == "README":
            continue
        base = DOC_METADATA.get(doc.stem, {"product_family": doc.stem, "product_ids": ""})
        for idx, chunk in enumerate(chunk_document(doc)):
            meta = {**base, "doc_file": doc.name, "section": chunk["section"]}
            yield _stable_id(doc.name, idx), chunk["text"], meta


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------


class KnowledgeIndex:
    """Chroma collection with caller-supplied embeddings."""

    def __init__(self, path: Path | str, embedder: Embedder) -> None:
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError as exc:
            raise RagUnavailable("chromadb is not installed") from exc
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(self.path), settings=Settings(anonymized_telemetry=False)
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=None,
            metadata={"hnsw:space": "cosine", "description": "Product knowledge base"},
        )
        self._embedder = embedder

    def count(self) -> int:
        return self._collection.count()

    def upsert(self, ids: list[str], texts: list[str], metadatas: list[dict[str, Any]]) -> None:
        if not ids:
            return
        self._collection.upsert(
            ids=ids, documents=texts, metadatas=metadatas, embeddings=self._embedder.encode(texts)
        )

    def query(self, text: str, top_k: int) -> list[KnowledgePassage]:
        total = self.count()
        if total == 0:
            return []
        result = self._collection.query(
            query_embeddings=self._embedder.encode([text]),
            n_results=min(top_k, total),
            include=["documents", "metadatas", "distances"],
        )
        passages = []
        for doc, meta, dist in zip(
            result["documents"][0], result["metadatas"][0], result["distances"][0]
        ):
            meta = meta or {}
            ids = [p for p in str(meta.get("product_ids", "")).split(",") if p]
            passages.append(
                KnowledgePassage(
                    text=doc,
                    doc_file=str(meta.get("doc_file", "unknown")),
                    section=str(meta.get("section", "")),
                    product_ids=ids,
                    product_family=meta.get("product_family"),
                    distance=float(dist) if dist is not None else None,
                )
            )
        return passages


def build_index(
    docs_dir: Path = DOCS_DIR,
    path: Optional[Path] = None,
    embedder: Optional[Embedder] = None,
) -> KnowledgeIndex:
    """Embed and upsert every document chunk (idempotent via stable ids)."""
    index = KnowledgeIndex(path or chroma_path(), embedder or SentenceTransformerEmbedder())
    ids, texts, metas = [], [], []
    for cid, text, meta in iter_chunks(docs_dir):
        ids.append(cid)
        texts.append(text)
        metas.append(meta)
    if not ids:
        raise RagUnavailable(f"no product documents found in {docs_dir}")
    index.upsert(ids, texts, metas)
    logger.info("Knowledge index at %s holds %d chunks", index.path, index.count())
    return index


# ---------------------------------------------------------------------------
# Process-level singleton
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_index: Optional[KnowledgeIndex] = None
_error: Optional[str] = None


def set_index(index: Optional[KnowledgeIndex], error: Optional[str] = None) -> None:
    """Install (or clear) the process index; used by tests and warm-up."""
    global _index, _error
    with _lock:
        _index, _error = index, error


def get_index() -> KnowledgeIndex:
    global _index, _error
    with _lock:
        if _index is not None:
            return _index
        if _error is not None:
            raise RagUnavailable(_error)
        try:
            index = KnowledgeIndex(chroma_path(), SentenceTransformerEmbedder())
            if index.count() == 0:
                raise RagUnavailable(
                    f"knowledge index at {chroma_path()} is empty; run scripts/ingest_knowledge.py"
                )
        except RagUnavailable as exc:
            _error = str(exc)
            logger.warning("Knowledge search unavailable: %s", exc)
            raise
        _index = index
        return index


def warm_up(build_if_missing: bool = True) -> None:
    """Load the index at start-up, building it from the docs when it is empty."""
    try:
        get_index()
    except RagUnavailable as exc:
        if not build_if_missing or "is empty" not in str(exc):
            return
        try:
            set_index(build_index())
        except RagUnavailable as build_exc:
            set_index(None, str(build_exc))
            logger.warning("Knowledge index build failed: %s", build_exc)


def status() -> dict[str, Any]:
    with _lock:
        if _index is not None:
            return {"available": True, "chunks": _index.count()}
        return {"available": False, "reason": _error or "not loaded"}


def search(query: str, top_k: int) -> KnowledgeResult:
    try:
        passages = get_index().query(query, top_k)
    except RagUnavailable as exc:
        return KnowledgeResult(
            available=False,
            query=query,
            message=f"Product knowledge search is unavailable: {exc}",
        )
    message = None if passages else "No relevant product documentation found"
    return KnowledgeResult(
        available=True, query=query, passages=passages, count=len(passages), message=message
    )
