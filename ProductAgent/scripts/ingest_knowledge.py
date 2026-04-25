"""
Ingest product knowledge documents into the ChromaDB vector store.

Run once before starting the server (and re-run whenever product docs change):

    python ProductAgent/scripts/ingest_knowledge.py

Or from within the ProductAgent directory:

    python scripts/ingest_knowledge.py

The script is idempotent — it upserts by stable doc IDs derived from the
filename and chunk index, so re-running only refreshes changed content.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve paths so the script works regardless of cwd
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).parent                     # ProductAgent/scripts/
_PRODUCT_AGENT_ROOT = _SCRIPTS_DIR.parent                # ProductAgent/
_UTILS_DIR = _PRODUCT_AGENT_ROOT / "product_agent" / "utils"
_DOCS_DIR = _PRODUCT_AGENT_ROOT / "data" / "product_docs"
_EMBEDDINGS_DIR = _PRODUCT_AGENT_ROOT / "data" / "embeddings"

# Add the ProductAgent root to sys.path so we can import the agent package
sys.path.insert(0, str(_PRODUCT_AGENT_ROOT))


# ---------------------------------------------------------------------------
# Chunking helpers
# ---------------------------------------------------------------------------

def _split_by_headings(text: str, filename: str) -> list[dict]:
    """
    Split markdown text on H2/H3 headings (## or ###).
    Returns list of dicts: {text, section, heading_level}
    """
    # Pattern: lines starting with ## or ### (but NOT ####)
    heading_pattern = re.compile(r'^(#{2,3})\s+(.+)$', re.MULTILINE)
    chunks = []
    positions = [(m.start(), m.group(2), len(m.group(1))) for m in heading_pattern.finditer(text)]

    if not positions:
        # No headings — treat entire file as one chunk
        stripped = text.strip()
        if stripped:
            chunks.append({"text": stripped, "section": filename, "heading_level": 0})
        return chunks

    # Everything before the first heading
    preamble = text[:positions[0][0]].strip()
    if preamble:
        chunks.append({"text": preamble, "section": "Overview", "heading_level": 0})

    for i, (pos, heading, level) in enumerate(positions):
        start = pos
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append({"text": chunk_text, "section": heading, "heading_level": level})

    return chunks


def _split_long_chunk(text: str, section: str, max_chars: int = 1800, overlap: int = 150) -> list[dict]:
    """
    Further split a chunk that exceeds max_chars into overlapping sub-chunks.
    Splits on paragraph boundaries where possible.
    """
    if len(text) <= max_chars:
        return [{"text": text, "section": section}]

    paragraphs = re.split(r'\n{2,}', text)
    sub_chunks = []
    current = ""
    current_section = section

    for para in paragraphs:
        if len(current) + len(para) + 2 > max_chars and current:
            sub_chunks.append({"text": current.strip(), "section": current_section})
            # Start next chunk with overlap from end of current
            current = current[-overlap:].lstrip() + "\n\n" + para
        else:
            current = current + ("\n\n" if current else "") + para

    if current.strip():
        sub_chunks.append({"text": current.strip(), "section": current_section})

    return sub_chunks


def chunk_document(filepath: Path) -> list[dict]:
    """
    Chunk a markdown document into sections, further splitting long sections.
    Returns list of dicts with keys: text, section.
    """
    text = filepath.read_text(encoding="utf-8")
    sections = _split_by_headings(text, filepath.stem)

    final_chunks = []
    for section in sections:
        sub = _split_long_chunk(section["text"], section["section"])
        final_chunks.extend(sub)

    return final_chunks


def _stable_id(filename: str, chunk_index: int) -> str:
    """Generate a stable, deterministic doc ID for upsert idempotency."""
    raw = f"{filename}::chunk_{chunk_index:04d}"
    return "prod_" + hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Metadata mapping  (filename → product_family + product_ids)
# ---------------------------------------------------------------------------
_DOC_METADATA: dict[str, dict] = {
    "fiber_internet": {
        "product_family": "fiber",
        "product_ids": "FIB-1G,FIB-5G,FIB-10G",
    },
    "coax_internet": {
        "product_family": "coax",
        "product_ids": "COAX-200M,COAX-500M,COAX-1G",
    },
    "voice_services": {
        "product_family": "voice",
        "product_ids": "VOICE-BAS,VOICE-STD,VOICE-ENT,VOICE-UCAAS",
    },
    "sd_wan": {
        "product_family": "sd-wan",
        "product_ids": "SDWAN-ESS,SDWAN-PRO,SDWAN-ENT",
    },
    "mobile_services": {
        "product_family": "mobile",
        "product_ids": "MOB-BAS,MOB-UNL,MOB-PREM",
    },
}


# ---------------------------------------------------------------------------
# Main ingestion
# ---------------------------------------------------------------------------

def ingest(docs_dir: Path = _DOCS_DIR, embeddings_dir: Path = _EMBEDDINGS_DIR) -> None:
    # Import directly from file path to avoid triggering product_agent/__init__.py
    # which eagerly imports google.adk (not needed for ingestion).
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location(
        "rag_manager",
        str(_PRODUCT_AGENT_ROOT / "product_agent" / "utils" / "rag_manager.py"),
    )
    _mod = _ilu.module_from_spec(_spec)  # type: ignore[arg-type]
    _spec.loader.exec_module(_mod)       # type: ignore[union-attr]
    ProductRAGManager = _mod.ProductRAGManager

    print(f"Vector store  : {embeddings_dir}")
    print(f"Docs directory: {docs_dir}\n")

    doc_files = sorted(docs_dir.glob("*.md"))
    if not doc_files:
        print("No .md files found in docs directory. Exiting.")
        sys.exit(1)

    rag = ProductRAGManager(vectorstore_path=embeddings_dir)
    total_chunks = 0

    for doc_path in doc_files:
        stem = doc_path.stem    # e.g. "fiber_internet"
        if stem == "README":
            continue            # skip the placeholder README

        doc_meta_base = _DOC_METADATA.get(stem, {"product_family": stem, "product_ids": ""})

        chunks = chunk_document(doc_path)
        texts, metadatas, ids = [], [], []

        for idx, chunk in enumerate(chunks):
            texts.append(chunk["text"])
            metadatas.append({
                **doc_meta_base,
                "doc_file": doc_path.name,
                "section": chunk.get("section", ""),
            })
            ids.append(_stable_id(doc_path.name, idx))

        rag.add_documents(documents=texts, metadatas=metadatas, ids=ids)
        total_chunks += len(chunks)
        print(f"  ✓ {doc_path.name:35s}  {len(chunks):3d} chunks")

    after_count = rag.document_count()
    print(f"\nIngestion complete. Total chunks in store: {after_count}")
    print("Vector store is ready — start the server and RAG will be available.")


if __name__ == "__main__":
    ingest()
