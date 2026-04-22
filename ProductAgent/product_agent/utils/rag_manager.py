"""
ProductRAGManager — ChromaDB-backed retrieval for product knowledge documents.

Designed for lazy initialization: importing this module never touches ChromaDB
or downloads the embedding model. The singleton is only created on the first
call to get_rag_manager(), so tests that don't need RAG and cold imports of
the agent never pay the startup cost.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path constants — resolved relative to this file so they are portable whether
# the module is imported standalone or via importlib from SuperAgent's CWD.
# ---------------------------------------------------------------------------
_UTILS_DIR = Path(__file__).parent          # ProductAgent/product_agent/utils/
_AGENT_DIR = _UTILS_DIR.parent              # ProductAgent/product_agent/
_PRODUCT_AGENT_ROOT = _AGENT_DIR.parent     # ProductAgent/
DEFAULT_VECTORSTORE_PATH = _PRODUCT_AGENT_ROOT / "data" / "embeddings"
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "product_knowledge"


class ProductRAGManager:
    """
    Manages product knowledge retrieval using ChromaDB + sentence-transformers.

    Single named collection ``product_knowledge`` stores all product docs.
    Metadata fields supported:
        - ``product_family``  e.g. "fiber", "coax", "voice", "sd-wan", "mobile"
        - ``doc_file``        source filename, e.g. "fiber_internet.md"
        - ``product_ids``     comma-separated IDs, e.g. "FIB-1G,FIB-5G,FIB-10G"
        - ``section``         heading text for the chunk
    """

    def __init__(
        self,
        vectorstore_path: Path | str = DEFAULT_VECTORSTORE_PATH,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    ) -> None:
        import chromadb
        from chromadb.config import Settings
        from sentence_transformers import SentenceTransformer

        self._vectorstore_path = Path(vectorstore_path)
        self._vectorstore_path.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=str(self._vectorstore_path),
            settings=Settings(anonymized_telemetry=False),
        )

        self._embedder = SentenceTransformer(embedding_model)

        # Get or create the single product knowledge collection
        try:
            self._collection = self._client.get_collection(name=COLLECTION_NAME)
        except Exception:
            self._collection = self._client.create_collection(
                name=COLLECTION_NAME,
                metadata={"description": "Product knowledge base for RAG Q&A"},
            )

    # ------------------------------------------------------------------
    # Document management
    # ------------------------------------------------------------------

    def add_documents(
        self,
        documents: list[str],
        metadatas: list[dict[str, Any]],
        ids: list[str] | None = None,
    ) -> None:
        """Embed and upsert documents into the collection. Idempotent via IDs."""
        if not documents:
            return

        if ids is None:
            ids = [
                f"doc_{hashlib.sha256(doc.encode()).hexdigest()[:12]}"
                for doc in documents
            ]

        embeddings = self._embedder.encode(documents, show_progress_bar=False).tolist()

        self._collection.upsert(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )

    def document_count(self) -> int:
        """Return the number of documents in the collection."""
        return self._collection.count()

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def query(
        self,
        query_text: str,
        n_results: int = 3,
        metadata_filter: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve the top-k most relevant document chunks.

        Returns a list of dicts with keys: ``text``, ``metadata``, ``distance``.
        """
        query_embedding = self._embedder.encode([query_text]).tolist()

        kwargs: dict[str, Any] = {
            "query_embeddings": query_embedding,
            "n_results": min(n_results, max(self._collection.count(), 1)),
        }
        if metadata_filter:
            kwargs["where"] = metadata_filter

        results = self._collection.query(**kwargs)

        output = []
        if results and results.get("documents"):
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                output.append({"text": doc, "metadata": meta, "distance": dist})

        return output

    def get_context(
        self,
        query_text: str,
        n_results: int = 3,
        metadata_filter: dict[str, str] | None = None,
    ) -> str:
        """
        Return a formatted markdown context block ready for prompt injection.
        Returns an empty string when no results are found.
        """
        hits = self.query(query_text, n_results=n_results, metadata_filter=metadata_filter)
        if not hits:
            return ""

        parts = []
        for i, hit in enumerate(hits, start=1):
            source = hit["metadata"].get("doc_file", "unknown")
            section = hit["metadata"].get("section", "")
            header = f"[Source {i}: {source}" + (f" — {section}" if section else "") + "]"
            parts.append(f"{header}\n{hit['text']}")

        return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# Lazy singleton — created once per process on first access
# ---------------------------------------------------------------------------
_instance: ProductRAGManager | None = None


def get_rag_manager() -> ProductRAGManager:
    """Return the process-level ProductRAGManager singleton (lazy init)."""
    global _instance
    if _instance is None:
        _instance = ProductRAGManager()
    return _instance
