import pytest

from sales_common.config import ConfigError, ContextSettings, model_name, safety_settings
from sales_common.logging import mask_url


def test_model_name_fails_fast(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    with pytest.raises(ConfigError, match="GEMINI_MODEL is required"):
        model_name()


def test_invalid_safety_level(monkeypatch):
    monkeypatch.setenv("SAFETY_HARASSMENT", "BLOCK_EVERYTHING")
    with pytest.raises(ConfigError):
        safety_settings()


def test_context_defaults(monkeypatch):
    for var in ("COMPACTION_INTERVAL", "CONTEXT_CACHE_TTL_SECONDS"):
        monkeypatch.delenv(var, raising=False)
    s = ContextSettings.from_env()
    assert (s.compaction_interval, s.compaction_overlap) == (8, 2)
    assert (s.compaction_token_threshold, s.compaction_retention) == (60_000, 10)
    assert (s.cache_ttl_seconds, s.cache_intervals) == (1800, 10)


def test_mask_url():
    assert mask_url("postgresql://u:secret@h:5432/db") == "postgresql://u:***@h:5432/db"
    assert "secret" not in mask_url("postgresql+asyncpg://u:secret@/db?host=/cloudsql/x")
    assert mask_url("http://h/x") == "http://h/x"
