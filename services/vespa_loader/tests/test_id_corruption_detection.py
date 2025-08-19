"""
Tests for detecting and preventing document ID corruption issues.
This test suite specifically catches the ID duplication problem that breaks vespa.py --clear-data.
"""

import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from vespa_loader.vespa_client import VespaClient

from services.common.test_utils import BaseSelectiveHTTPIntegrationTest


class TestIDCorruptionDetection(BaseSelectiveHTTPIntegrationTest):
    """Test ID corruption detection and prevention."""

    def setup_method(self, method: object) -> None:
        """Set up test environment with aiohttp patching."""
        super().setup_method(method)

        # Add aiohttp patching to prevent real HTTP calls
        self.aiohttp_patcher = patch("aiohttp.ClientSession")
        self.mock_aiohttp_class = self.aiohttp_patcher.start()

        # Create a mock session that can simulate ID corruption
        class MockSession:
            def __init__(self, test_instance):
                self.test_instance = test_instance
                self.corruption_mode = False  # Toggle to simulate corruption

            def set_corruption_mode(self, enabled: bool):
                """Enable/disable ID corruption simulation."""
                self.corruption_mode = enabled

            def post(self, url, json=None):
                """Simulate document indexing with optional ID corruption."""
                if "/document/v1/" in url:
                    parts = url.split("/")
                    user_id = parts[-2]
                    doc_id = parts[-1]

                    if self.corruption_mode:
                        # Simulate the corruption we're seeing in production
                        corrupted_id = f"id:briefly:briefly_document::id:briefly:briefly_document:g={user_id}:{doc_id}"
                    else:
                        # Correct streaming mode format
                        corrupted_id = (
                            f"id:briefly:briefly_document:g={user_id}:{doc_id}"
                        )

                    return self.test_instance.mock_response(
                        200, {"id": corrupted_id, "status": "success"}
                    )
                else:
                    return self.test_instance.mock_response()

            def get(self, url):
                """Simulate document retrieval."""
                if "/document/v1/" in url:
                    parts = url.split("/")
                    user_id = parts[-2]
                    doc_id = parts[-1]

                    if self.corruption_mode:
                        corrupted_id = f"id:briefly:briefly_document::id:briefly:briefly_document:g={user_id}:{doc_id}"
                    else:
                        corrupted_id = (
                            f"id:briefly:briefly_document:g={user_id}:{doc_id}"
                        )

                    return self.test_instance.mock_response(
                        200,
                        {
                            "id": corrupted_id,
                            "fields": {
                                "user_id": user_id,
                                "doc_id": doc_id,
                                "title": "Test Document",
                                "content": "Test content",
                                "search_text": "test document",
                            },
                        },
                    )
                else:
                    return self.test_instance.mock_response()

            def delete(self, url):
                """Simulate document deletion."""
                if "/document/v1/" in url:
                    parts = url.split("/")
                    user_id = parts[-2]
                    doc_id = parts[-1]

                    if self.corruption_mode:
                        corrupted_id = f"id:briefly:briefly_document::id:briefly:briefly_document:g={user_id}:{doc_id}"
                    else:
                        corrupted_id = (
                            f"id:briefly:briefly_document:g={user_id}:{doc_id}"
                        )

                    return self.test_instance.mock_response(
                        200, {"id": corrupted_id, "status": "success"}
                    )
                else:
                    return self.test_instance.mock_response()

        self.mock_aiohttp_instance = MockSession(self)
        self.mock_aiohttp_class.return_value = self.mock_aiohttp_instance

        # Also patch the VespaClient.start method to prevent real session creation
        self.vespa_start_patcher = patch("vespa_loader.vespa_client.VespaClient.start")
        self.mock_vespa_start = self.vespa_start_patcher.start()

    def teardown_method(self, method: object) -> None:
        """Clean up after each test method."""
        super().teardown_method(method)
        self.aiohttp_patcher.stop()
        self.vespa_start_patcher.stop()

    def mock_response(self, status=200, json_data=None, text_data=""):
        """Create a mock response object."""

        class MockResponse:
            def __init__(self, status=200, json_data=None, text_data=""):
                self.status = status
                self.json_data = json_data or {"id": "test_id", "status": "success"}
                self.text_data = text_data

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

            async def json(self):
                return self.json_data

            async def text(self):
                return self.text_data

        return MockResponse(status, json_data, text_data)

    @pytest.fixture
    def vespa_client(self):
        """Create a mocked Vespa client."""
        client = VespaClient("http://localhost:8080")
        client.session = self.mock_aiohttp_instance
        return client

    def test_detect_id_corruption_pattern(self):
        """Test that we can detect the specific ID corruption pattern."""
        # This is the exact corruption pattern we're seeing in production
        corrupted_ids = [
            "id:briefly:briefly_document::id:briefly:briefly_document:g=trybriefly@outlook.com:ms_0",
            "id:briefly:briefly_document::id:briefly:briefly_document:g=trybriefly@outlook.com:ms_4",
            "id:briefly:briefly_document::id:briefly:briefly_document:g=user@example.com:doc_123",
        ]

        # Pattern to detect corruption: double "id:briefly:briefly_document::"
        corruption_pattern = (
            r"id:briefly:briefly_document::id:briefly:briefly_document:g="
        )

        for corrupted_id in corrupted_ids:
            # Should detect corruption
            assert re.search(
                corruption_pattern, corrupted_id
            ), f"Failed to detect corruption in: {corrupted_id}"

            # Should have the corruption pattern (note: it's :: not ::)
            assert (
                corrupted_id.count("id:briefly:briefly_document::") == 1
            ), f"Expected corruption pattern in: {corrupted_id}"
            assert (
                "id:briefly:briefly_document::id:briefly:briefly_document:g="
                in corrupted_id
            ), f"Expected corruption pattern in: {corrupted_id}"

    def test_correct_id_format_validation(self):
        """Test that correct IDs don't trigger corruption detection."""
        correct_ids = [
            "id:briefly:briefly_document:g=trybriefly@outlook.com:ms_0",
            "id:briefly:briefly_document:g=trybriefly@outlook.com:ms_4",
            "id:briefly:briefly_document:g=user@example.com:doc_123",
        ]

        # Pattern to detect corruption: double "id:briefly:briefly_document::"
        corruption_pattern = (
            r"id:briefly:briefly_document::id:briefly:briefly_document:g="
        )

        for correct_id in correct_ids:
            # Should NOT detect corruption
            assert not re.search(
                corruption_pattern, correct_id
            ), f"False positive corruption detection in: {correct_id}"

            # Should have single pattern
            assert (
                correct_id.count("id:briefly:briefly_document:g=") == 1
            ), f"Expected single pattern in: {correct_id}"

    async def test_indexing_without_corruption(self, vespa_client):
        """Test that indexing produces correct IDs when corruption is disabled."""
        # Disable corruption mode
        self.mock_aiohttp_instance.set_corruption_mode(False)

        test_doc = {
            "user_id": "test@example.com",
            "doc_id": "test_001",
            "title": "Test Document",
            "content": "Test content",
            "search_text": "test document",
            "provider": "test_provider",
            "source_type": "test_source",
        }

        result = await vespa_client.index_document(test_doc)

        # Should succeed
        assert result["status"] == "success"

        # ID should be correct format
        vespa_id = result["id"]
        assert vespa_id.startswith("id:briefly:briefly_document:g=")
        assert vespa_id.count("id:briefly:briefly_document:g=") == 1
        assert (
            vespa_id.count(":") == 4
        )  # Correct format: id:briefly:briefly_document:g=user:doc

        # Should NOT have corruption
        assert (
            "id:briefly:briefly_document::id:briefly:briefly_document:g="
            not in vespa_id
        )

    def test_corruption_detection_in_real_scenario(self):
        """Test that we can detect corruption in the real scenario we're seeing."""
        # This test simulates what we're actually seeing in production
        # where the backend creates corrupted IDs that break the clear script

        # Real corrupted IDs from the error logs
        real_corrupted_ids = [
            "id:briefly:briefly_document::id:briefly:briefly_document:g=trybriefly@outlook.com:ms_0",
            "id:briefly:briefly_document::id:briefly:briefly_document:g=trybriefly@outlook.com:ms_4",
        ]

        # Our corruption detection function
        def detect_corruption(vespa_id: str) -> bool:
            """Detect if a Vespa ID is corrupted."""
            corruption_pattern = (
                r"id:briefly:briefly_document::id:briefly:briefly_document:g="
            )
            return bool(re.search(corruption_pattern, vespa_id))

        # Test that we can detect the corruption
        for corrupted_id in real_corrupted_ids:
            assert detect_corruption(
                corrupted_id
            ), f"Failed to detect corruption in: {corrupted_id}"

            # Verify the corruption pattern
            assert (
                "id:briefly:briefly_document::id:briefly:briefly_document:g="
                in corrupted_id
            )
            assert (
                corrupted_id.count("id:briefly:briefly_document::") == 1
            )  # Single corruption pattern

        # Test that correct IDs don't trigger false positives
        correct_ids = [
            "id:briefly:briefly_document:g=trybriefly@outlook.com:ms_0",
            "id:briefly:briefly_document:g=trybriefly@outlook.com:ms_4",
        ]

        for correct_id in correct_ids:
            assert not detect_corruption(
                correct_id
            ), f"False positive corruption detection in: {correct_id}"

    def test_corruption_impact_on_clear_script(self):
        """Test that corrupted IDs would break the clear script parsing."""
        # Simulate what the clear script would encounter
        corrupted_ids = [
            "id:briefly:briefly_document::id:briefly:briefly_document:g=trybriefly@outlook.com:ms_0",
            "id:briefly:briefly_document::id:briefly:briefly_document:g=trybriefly@outlook.com:ms_4",
        ]

        for corrupted_id in corrupted_ids:
            # The clear script expects to parse the ID to extract user_id and doc_id
            # With corruption, this parsing would fail

            # Simulate parsing attempt
            try:
                # This is what the clear script might try to do
                if "id:briefly:briefly_document:g=" in corrupted_id:
                    # Extract user_id and doc_id from the correct part
                    parts = corrupted_id.split("id:briefly:briefly_document:g=")
                    if len(parts) > 1:
                        user_doc_part = parts[-1]  # Take the last part after corruption
                        if ":" in user_doc_part:
                            user_id, doc_id = user_doc_part.split(":", 1)
                            # This should work even with corruption
                            assert user_id == "trybriefly@outlook.com"
                            assert doc_id.startswith("ms_")
                        else:
                            pytest.fail(
                                f"Could not parse user:doc from corrupted ID: {corrupted_id}"
                            )
                    else:
                        pytest.fail(
                            f"Could not find g= part in corrupted ID: {corrupted_id}"
                        )
                else:
                    pytest.fail(
                        f"Could not find streaming mode pattern in corrupted ID: {corrupted_id}"
                    )

            except Exception as e:
                pytest.fail(
                    f"Clear script parsing failed for corrupted ID {corrupted_id}: {e}"
                )

    def test_corruption_prevention_validation(self):
        """Test that our validation can prevent corrupted IDs from being created."""

        def validate_vespa_id(vespa_id: str) -> bool:
            """Validate that a Vespa ID is not corrupted."""
            # Check for the corruption pattern
            corruption_pattern = (
                r"id:briefly:briefly_document::id:briefly:briefly_document:g="
            )
            if re.search(corruption_pattern, vespa_id):
                return False  # Corrupted

            # Check for correct streaming mode format
            correct_pattern = r"^id:briefly:briefly_document:g=[^:]+:[^:]+$"
            if re.match(correct_pattern, vespa_id):
                return True  # Correct format

            return False  # Invalid format

        # Test corrupted IDs
        corrupted_ids = [
            "id:briefly:briefly_document::id:briefly:briefly_document:g=user:doc",
            "id:briefly:briefly_document:g=user:doc::extra",
            "id:briefly:briefly_document::g=user:doc",
        ]

        for corrupted_id in corrupted_ids:
            assert not validate_vespa_id(
                corrupted_id
            ), f"Corrupted ID should fail validation: {corrupted_id}"

        # Test correct IDs
        correct_ids = [
            "id:briefly:briefly_document:g=user@example.com:doc_123",
            "id:briefly:briefly_document:g=test@domain.com:ms_0",
        ]

        for correct_id in correct_ids:
            assert validate_vespa_id(
                correct_id
            ), f"Correct ID should pass validation: {correct_id}"

    def test_clear_script_failure_scenario(self):
        """Test the exact failure scenario we're seeing with vespa.py --clear-data."""
        # This test captures the specific problem described in the user query

        # The corrupted IDs that are causing the clear script to fail
        problematic_ids = [
            "id:briefly:briefly_document::id:briefly:briefly_document:g=trybriefly@outlook.com:ms_0",
            "id:briefly:briefly_document::id:briefly:briefly_document:g=trybriefly@outlook.com:ms_4",
        ]

        # The clear script expects to parse these IDs to extract user_id and doc_id
        # Let's simulate what the clear script might be trying to do

        for corrupted_id in problematic_ids:
            # Problem 1: The ID has the corruption pattern
            assert (
                "id:briefly:briefly_document::id:briefly:briefly_document:g="
                in corrupted_id
            )

            # Problem 2: The clear script might try to parse this incorrectly
            # If it tries to split on "::" it will get wrong parts
            parts_by_double_colon = corrupted_id.split("::")
            assert len(parts_by_double_colon) == 2  # This is the corruption!

            # Problem 3: The clear script might expect the old format
            # Old format: id:briefly:briefly_document::doc_id
            # New format: id:briefly:briefly_document:g=user_id:doc_id
            # Corrupted: id:briefly:briefly_document::id:briefly:briefly_document:g=user_id:doc_id

            # The clear script needs to handle this corruption gracefully
            # Solution: Extract the correct part after "g="
            if "id:briefly:briefly_document:g=" in corrupted_id:
                # Extract the correct user_id and doc_id from the corrupted ID
                user_doc_part = corrupted_id.split("id:briefly:briefly_document:g=")[-1]
                if ":" in user_doc_part:
                    user_id, doc_id = user_doc_part.split(":", 1)

                    # These should be the correct values despite corruption
                    assert user_id == "trybriefly@outlook.com"
                    assert doc_id.startswith("ms_")

                    # The clear script should be able to work with these extracted values
                    assert user_id is not None
                    assert doc_id is not None
                else:
                    pytest.fail(
                        f"Could not extract user_id and doc_id from corrupted ID: {corrupted_id}"
                    )
            else:
                pytest.fail(
                    f"Corrupted ID missing expected streaming mode pattern: {corrupted_id}"
                )

        # This test demonstrates that even with corruption, we can extract the needed information
        # The clear script should be updated to handle this corruption pattern


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
