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


# ---------------------------------------------------------------------------
# FAQ corpus
# ---------------------------------------------------------------------------


def test_faq_chunking_covers_all_topics():
    chunks = list(rag.iter_faq_chunks())
    topics = {meta["topic"] for _, _, meta in chunks}
    assert topics == {
        "billing_and_payments",
        "cancellation_and_changes",
        "contracts_and_terms",
        "installation",
        "service_levels",
        "support",
    }
    ids = [cid for cid, _, _ in chunks]
    assert len(ids) == len(set(ids)) and all(cid.startswith("faq_") for cid in ids)


@pytest.fixture(scope="module")
def hashed_faq_index(tmp_path_factory):
    index = rag.build_faq_index(path=tmp_path_factory.mktemp("chroma_faq"), embedder=HashingEmbedder())
    rag.set_faq_index(index)
    yield index
    rag.set_faq_index(None, None)


@pytest.mark.parametrize(
    "question, topic",
    [
        ("What contract lengths do you offer?", "contracts_and_terms"),
        ("What is your cancellation policy?", "cancellation_and_changes"),
        ("When can I reach technical support?", "support"),
        ("Which payment methods do you accept?", "billing_and_payments"),
        ("Do you offer self-install kits?", "installation"),
        ("What is your uptime guarantee?", "service_levels"),
    ],
)
def test_faq_search_returns_matching_topic(hashed_faq_index, question, topic):
    # The hashing embedder is bag-of-words, so the right topic must be in the top 2
    # (the real model ranks it first; see test_faq_real_embedding_model).
    result = core.search_faq(question, 3)
    assert result.available and result.count >= 1
    assert topic in {p.topic for p in result.passages[:2]}


def test_faq_chunks_have_answer_text():
    assert all(not text.lstrip().startswith("# ") or "\n" in text for _, text, _ in rag.iter_faq_chunks())
    assert all(meta["section"] != "Overview" for _, _, meta in rag.iter_faq_chunks())


def test_faq_real_embedding_model(tmp_path):
    try:
        embedder = rag.SentenceTransformerEmbedder()
    except rag.RagUnavailable as exc:
        pytest.skip(f"embedding model unavailable: {exc}")
    index = rag.build_faq_index(path=tmp_path / "chroma", embedder=embedder)
    expected = {
        "What contract lengths do you offer?": "contracts_and_terms",
        "What is your cancellation policy?": "cancellation_and_changes",
        "When can I reach technical support?": "support",
        "Which payment methods do you accept?": "billing_and_payments",
        "Do you offer self-install kits?": "installation",
        "What is your uptime guarantee?": "service_levels",
        "Is there an early termination fee?": "cancellation_and_changes",
    }
    for question, topic in expected.items():
        assert index.raw_query(question, 1)[0][1]["topic"] == topic, question


def test_faq_and_product_collections_are_separate(hashed_faq_index, tmp_path):
    product = rag.build_index(path=tmp_path / "c", embedder=HashingEmbedder())
    faq = rag.build_faq_index(path=tmp_path / "c", embedder=HashingEmbedder())
    assert product.count() == len(list(rag.iter_chunks()))
    assert faq.count() == len(list(rag.iter_faq_chunks()))


def test_faq_unavailable_when_index_missing(monkeypatch):
    rag.set_faq_index(None, "no index")
    result = rag.search_faq("support hours", 3)
    assert result.available is False and "unavailable" in result.message
    assert rag.faq_status()["available"] is False
    rag.set_faq_index(None, None)


def test_faq_rejects_empty_query():
    with pytest.raises(core.InvalidInputError):
        core.search_faq("  ", 3)


def test_concurrent_search_on_shared_embedder(tmp_path):
    """Product and FAQ searches from many threads at once must not crash the process.

    Regression: two models on Apple's MPS backend encoding concurrently segfaulted
    the catalog service. Embeddings now run on one shared CPU model behind a lock.
    """
    from concurrent.futures import ThreadPoolExecutor

    try:
        embedder = rag.shared_embedder()
    except rag.RagUnavailable as exc:
        pytest.skip(f"embedding model unavailable: {exc}")
    assert embedder.device == "cpu"
    product = rag.build_index(path=tmp_path / "c", embedder=embedder)
    faq = rag.build_faq_index(path=tmp_path / "c", embedder=embedder)
    questions = ["fiber uptime SLA", "cancellation policy", "support hours", "SD-WAN sites"] * 10

    def ask(i):
        index = product if i % 2 else faq
        return len(index.raw_query(questions[i], 3))

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert all(n > 0 for n in pool.map(ask, range(len(questions))))
