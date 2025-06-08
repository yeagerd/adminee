import pytest
from typing import Dict, Any, Optional

# Assuming generate_cache_key is in core.cache_manager
from core.cache_manager import generate_cache_key

# Test cases for generate_cache_key
@pytest.mark.parametrize(
    "user_id, endpoint, provider, params, expected_prefix",
    [
        ("user123", "get_emails", "google", {"folder": "inbox"}, "office_service:user123:google:get_emails:"),
        ("user456", "get_events", "microsoft", None, "office_service:user456:microsoft:get_events:"),
        ("user789", "get_files", None, {"limit": 10}, "office_service:user789:get_files:"),
        ("test_user", "some_endpoint", "google", {"a": 1, "b": 2}, "office_service:test_user:google:some_endpoint:"),
        ("test_user", "some_endpoint", "google", {"b": 2, "a": 1}, "office_service:test_user:google:some_endpoint:"), # Order shouldn't matter
    ],
)
def test_generate_cache_key_structure_and_determinism(
    user_id: str, endpoint: str, provider: Optional[str], params: Optional[Dict[str, Any]], expected_prefix: str
):
    key1 = generate_cache_key(user_id, endpoint, provider, params)
    key2 = generate_cache_key(user_id, endpoint, provider, params) # Call again to check determinism

    assert key1.startswith(expected_prefix)
    assert key1 == key2 # Keys should be identical for identical inputs

    if params:
        # Check that different params produce different keys
        modified_params = params.copy()
        modified_params["_some_diff_"] = "value" # Add a unique value
        key_diff_params = generate_cache_key(user_id, endpoint, provider, modified_params)
        assert key1 != key_diff_params
    else:
        # Check that adding params produces a different key
        key_with_params = generate_cache_key(user_id, endpoint, provider, {"new_param": True})
        assert key1 != key_with_params


def test_generate_cache_key_param_order_does_not_matter():
    key1 = generate_cache_key("user", "ep", "prov", {"param1": "val1", "param2": "val2"})
    key2 = generate_cache_key("user", "ep", "prov", {"param2": "val2", "param1": "val1"})
    assert key1 == key2

def test_generate_cache_key_empty_vs_none_params():
    key_none_params = generate_cache_key("user", "ep", "prov", None)
    key_empty_params = generate_cache_key("user", "ep", "prov", {}) # Empty dict should be different from None if not handled
    # Current implementation treats None and empty string for params differently for hash
    # json.dumps(None) -> "null", json.dumps({}) -> "{}"
    assert key_none_params != key_empty_params, "None params and empty dict params should ideally produce different keys or be normalized"
    # If they should be the same, the generate_cache_key function would need to normalize (e.g. params = params or {}) before hashing.
    # For now, design doc implies `params: Dict` which means empty dict is valid, None means no params.

# Note: Testing get_from_cache and set_to_cache would require a running Redis
# or a mock Redis instance (e.g., using fakeredis or mocking redis.asyncio.Redis).
# This is often set up in a conftest.py for broader test suites.
# For this subtask, we focus on generate_cache_key which is pure Python.
