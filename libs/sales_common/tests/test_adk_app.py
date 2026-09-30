from google.adk import Agent

from sales_common.adk_app import build_app
from sales_common.config import ContextSettings


def test_build_app_enables_compaction_and_cache():
    agent = Agent(name="probe_agent", model="gemini-test", instruction="x")
    app = build_app("probe_agent", agent, settings=ContextSettings(8, 2, 60000, 10, 10, 1800, 4096))
    assert app.events_compaction_config.compaction_interval == 8
    assert app.events_compaction_config.overlap_size == 2
    assert app.events_compaction_config.token_threshold == 60000
    assert app.context_cache_config.ttl_seconds == 1800
    assert app.context_cache_config.cache_intervals == 10
    assert app.context_cache_config.min_tokens == 4096
