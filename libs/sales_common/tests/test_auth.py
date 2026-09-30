from sales_common import auth


def test_none_mode_has_no_headers(monkeypatch):
    monkeypatch.setenv("SERVICE_AUTH", "none")
    assert auth.service_headers("http://order-agent:8205/") == {}


def test_id_token_mode_uses_audience_and_cache(monkeypatch):
    monkeypatch.setenv("SERVICE_AUTH", "gcp_id_token")
    auth._cache.clear()
    calls = []

    def fetcher(aud):
        calls.append(aud)
        return f"tok-{len(calls)}"

    h1 = auth.service_headers("https://svc-abc.a.run.app/mcp/", fetcher)
    h2 = auth.service_headers("https://svc-abc.a.run.app/other", fetcher)
    assert h1 == h2 == {"Authorization": "Bearer tok-1"}
    assert calls == ["https://svc-abc.a.run.app"]
