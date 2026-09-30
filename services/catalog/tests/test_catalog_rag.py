"""Knowledge index tests.

The pipeline (chunking, Chroma persistence, metadata, query) is tested with a
deterministic hashing embedder, so no model download is needed. The real
sentence-transformers model is exercised only when it is installed and loadable.
"""

import hashlib
import math
import re

import pytest

from catalog_service import core, rag


class HashingEmbedder:
    """Bag-of-words feature hashing; deterministic and dependency-free."""

    dim = 512

    def encode(self, texts):
        vectors = []
        for text in texts:
            vec = [0.0] * self.dim
            for token in re.findall(r"[a-z0-9]+", text.lower()):
                h = int(hashlib.md5(token.encode()).hexdigest(), 16)
                vec[h % self.dim] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vectors.append([v / norm for v in vec])
        return vectors


chromadb = pytest.importorskip("chromadb")


def test_chunking_covers_all_docs():
    chunks = list(rag.iter_chunks())
    files = {meta["doc_file"] for _, _, meta in chunks}
    assert files == {
        "fiber_internet.md",
        "coax_internet.md",
        "voice_services.md",
        "sd_wan.md",
        "mobile_services.md",
    }
    ids = [cid for cid, _, _ in chunks]
    assert len(ids) == len(set(ids))
    assert all(len(text) <= 1800 + 200 for _, text, _ in chunks)


@pytest.fixture(scope="module")
def hashed_index(tmp_path_factory):
    index = rag.build_index(path=tmp_path_factory.mktemp("chroma"), embedder=HashingEmbedder())
    rag.set_index(index)
    yield index
    rag.set_index(None, None)


def test_build_is_idempotent(hashed_index):
    before = hashed_index.count()
    ids, texts, metas = zip(*rag.iter_chunks())
    hashed_index.upsert(list(ids), list(texts), list(metas))
    assert hashed_index.count() == before > 20


def test_sla_question_returns_fiber_passage(hashed_index):
    result = core.search_product_knowledge("fiber SLA uptime")
    assert result.available is True
    assert 1 <= result.count <= core.DEFAULT_TOP_K
    assert any(p.doc_file == "fiber_internet.md" for p in result.passages)
    fiber = next(p for p in result.passages if p.doc_file == "fiber_internet.md")
    assert fiber.section
    assert fiber.product_ids == ["FIB-1G", "FIB-5G", "FIB-10G"]


def test_top_k_respected(hashed_index):
    assert core.search_product_knowledge("SD-WAN sites ZTNA", top_k=2).count == 2
    assert core.search_product_knowledge("SD-WAN sites ZTNA", top_k=10).count == 10


def test_unavailable_when_index_missing(tmp_path, monkeypatch):
    rag.set_index(None, None)
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "empty"))
    result = rag.search("fiber SLA uptime", 4)
    assert result.available is False
    assert result.message
    assert rag.status()["available"] is False
    rag.set_index(None, None)


def test_real_embedding_model(tmp_path):
    pytest.importorskip("sentence_transformers")
    try:
        embedder = rag.SentenceTransformerEmbedder()
    except rag.RagUnavailable as exc:
        pytest.skip(str(exc))
    index = rag.build_index(path=tmp_path / "chroma", embedder=embedder)
    passages = index.query("fiber SLA uptime", 4)
    assert any(p.doc_file == "fiber_internet.md" for p in passages)
