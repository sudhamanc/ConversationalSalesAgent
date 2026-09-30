"""Build the product-knowledge ChromaDB index from ``data/product_docs``.

Run at image build time (see Dockerfile) or whenever the docs change::

    python services/catalog/scripts/ingest_knowledge.py [--docs DIR] [--chroma-path DIR]

Idempotent: chunks are upserted by stable ids derived from file name and chunk
index. The index location defaults to ``CHROMA_PATH`` and the embedding model
to ``EMBEDDING_MODEL_PATH`` / ``EMBEDDING_MODEL`` (see ``catalog_service.rag``).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))

from catalog_service import rag  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the product knowledge index")
    parser.add_argument("--docs", type=Path, default=rag.DOCS_DIR)
    parser.add_argument("--chroma-path", type=Path, default=None)
    args = parser.parse_args(argv)
    path = args.chroma_path or rag.chroma_path()
    print(f"Docs directory: {args.docs}\nVector store  : {path}")
    try:
        index = rag.build_index(docs_dir=args.docs, path=path)
    except rag.RagUnavailable as exc:
        print(f"Index build failed: {exc}", file=sys.stderr)
        return 1
    print(f"Ingestion complete. Total chunks in store: {index.count()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
