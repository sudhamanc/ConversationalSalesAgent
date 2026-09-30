from sales_common.mcp_client import mcp_result_payload


def test_structured_content_object():
    assert mcp_result_payload({"structuredContent": {"found": True}}) == {"found": True}


def test_structured_content_result_wrapper_unwrapped():
    raw = {"structuredContent": {"result": {"found": True, "product_id": "FIB-1G"}}, "isError": False}
    assert mcp_result_payload(raw) == {"found": True, "product_id": "FIB-1G"}
    assert mcp_result_payload({"structured_content": {"result": {"a": 1}}}) == {"a": 1}


def test_result_wrapper_kept_for_non_objects_or_extra_keys():
    assert mcp_result_payload({"structuredContent": {"result": [1, 2]}}) == {"result": [1, 2]}
    both = {"result": {"a": 1}, "count": 1}
    assert mcp_result_payload({"structuredContent": both}) == both


def test_text_fallback_and_errors():
    assert mcp_result_payload({"content": [{"type": "text", "text": '{"x": 1}'}]}) == {"x": 1}
    assert mcp_result_payload({"isError": True, "structuredContent": {"x": 1}}) is None
    assert mcp_result_payload("nope") is None
