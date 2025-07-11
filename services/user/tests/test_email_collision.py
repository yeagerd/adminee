"""
Unit tests for email collision detection functionality.

Tests email normalization and collision detection using fast local provider-specific rules.
No DNS lookups are performed - all normalization uses local rules for Gmail, Outlook, Yahoo, etc.
"""

import contextlib
import os
import tempfile
import uuid
from unittest.mock import patch

import pytest
import pytest_asyncio

from services.user.database import create_all_tables, get_async_session
from services.user.models.user import User
from services.user.utils.email_collision import (
    EmailCollisionDetector,
    email_collision_detector,
)

# ------------------- Normalization Unit Tests (No DB) -------------------


class TestEmailNormalization:
    def setup_method(self):
        self.detector = EmailCollisionDetector()

    def test_normalize_email_gmail(self):
        test_cases = [
            ("user@gmail.com", "user@gmail.com"),
            ("User@gmail.com", "user@gmail.com"),
            ("user+work@gmail.com", "user@gmail.com"),
            ("first.last@gmail.com", "firstlast@gmail.com"),
            ("F.I.R.S.T.L.A.S.T@gmail.com", "firstlast@gmail.com"),
            ("user+work+personal@gmail.com", "user@gmail.com"),
        ]
        for input_email, expected in test_cases:
            # Fast local normalization handles Gmail rules (dots and plus addressing)
            result = self.detector.normalize_email(input_email)
            assert result == expected

    def test_normalize_email_outlook(self):
        test_cases = [
            ("user@outlook.com", "user@outlook.com"),
            ("user+work@outlook.com", "user@outlook.com"),
            ("first.last@outlook.com", "first.last@outlook.com"),
            ("User@Outlook.com", "user@outlook.com"),
        ]
        for input_email, expected in test_cases:
            # Fast local normalization handles Outlook rules (plus addressing only)
            result = self.detector.normalize_email(input_email)
            assert result == expected

    def test_normalize_email_yahoo(self):
        test_cases = [
            ("user@yahoo.com", "user@yahoo.com"),
            ("user+work@yahoo.com", "user@yahoo.com"),
            ("first.last@yahoo.com", "firstlast@yahoo.com"),
            ("User@Yahoo.com", "user@yahoo.com"),
        ]
        for input_email, expected in test_cases:
            # Fast local normalization handles Yahoo rules (dots and plus addressing)
            result = self.detector.normalize_email(input_email)
            assert result == expected

    def test_normalize_email_custom_domain(self):
        test_cases = [
            ("user@company.com", "user@company.com"),
            ("User@Company.com", "user@company.com"),
            ("user+work@company.com", "user+work@company.com"),
        ]
        for input_email, expected in test_cases:
            # Fast local normalization handles custom domains with basic lowercasing
            result = self.detector.normalize_email(input_email)
            assert result == expected

    def test_normalize_email_empty_input(self):
        result = self.detector.normalize_email("")
        assert result == ""

    def test_normalize_email_fallback(self):
        # Test the fallback behavior by mocking the simple_email_normalize to fail
        with patch.object(
            self.detector,
            "_simple_email_normalize",
            side_effect=Exception("Normalization failed"),
        ):
            result = self.detector.normalize_email("User@Gmail.com")
            # Should fallback to basic strip().lower()
            assert result == "user@gmail.com"

    def test_normalize_email_by_provider_google(self):
        test_cases = [
            ("user@gmail.com", "google", "user@gmail.com"),
            ("user+work@gmail.com", "google", "user@gmail.com"),
            ("first.last@gmail.com", "google", "firstlast@gmail.com"),
            ("user@googlemail.com", "google", "user@gmail.com"),  # Domain normalization
            ("User@Gmail.com", "google", "user@gmail.com"),
        ]
        for input_email, provider, expected in test_cases:
            result = self.detector.normalize_email_by_provider(input_email, provider)
            assert result == expected

    def test_normalize_email_by_provider_microsoft(self):
        test_cases = [
            ("user@outlook.com", "microsoft", "user@outlook.com"),
            ("user+work@outlook.com", "microsoft", "user@outlook.com"),
            (
                "first.last@outlook.com",
                "microsoft",
                "first.last@outlook.com",
            ),  # Keep dots
            (
                "user@hotmail.com",
                "microsoft",
                "user@outlook.com",
            ),  # Domain normalization
            ("User@Live.com", "microsoft", "user@outlook.com"),  # Domain normalization
        ]
        for input_email, provider, expected in test_cases:
            result = self.detector.normalize_email_by_provider(input_email, provider)
            assert result == expected

    def test_normalize_email_by_provider_yahoo(self):
        test_cases = [
            ("user@yahoo.com", "yahoo", "user@yahoo.com"),
            ("user+work@yahoo.com", "yahoo", "user@yahoo.com"),
            ("first.last@yahoo.com", "yahoo", "firstlast@yahoo.com"),
            ("User@Yahoo.com", "yahoo", "user@yahoo.com"),
        ]
        for input_email, provider, expected in test_cases:
            result = self.detector.normalize_email_by_provider(input_email, provider)
            assert result == expected

    def test_normalize_email_by_provider_unknown(self):
        # Unknown providers should only get basic normalization
        test_cases = [
            ("user@company.com", "unknown", "user@company.com"),
            ("User@Company.com", "other", "user@company.com"),
            (
                "user+work@company.com",
                "custom",
                "user+work@company.com",
            ),  # Plus addressing preserved
        ]
        for input_email, provider, expected in test_cases:
            result = self.detector.normalize_email_by_provider(input_email, provider)
            assert result == expected

    def test_get_email_domain(self):
        test_cases = [
            ("user@gmail.com", "gmail.com"),
            ("user@googlemail.com", "googlemail.com"),
            ("user@outlook.com", "outlook.com"),
            ("user@hotmail.com", "hotmail.com"),
            ("user@yahoo.com", "yahoo.com"),
            ("user@icloud.com", "icloud.com"),
            ("user@me.com", "me.com"),
            ("user@company.com", "company.com"),
            ("invalid-email", "unknown"),
        ]
        for input_email, expected in test_cases:
            result = self.detector._get_email_domain(input_email)
            assert result == expected


# ------------------- DB Collision Tests (with DB) -------------------


@pytest_asyncio.fixture(scope="function")
async def db_setup(monkeypatch):
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.environ["DB_URL_USER_MANAGEMENT"] = f"sqlite+aiosqlite:///{db_path}"
    await create_all_tables()
    yield
    os.close(db_fd)
    os.unlink(db_path)


@pytest_asyncio.fixture(scope="function")
async def detector_fixture():
    return EmailCollisionDetector()


class TestEmailCollisionDB:
    @pytest.mark.asyncio
    async def test_check_collision_no_collision(self, db_setup, detector_fixture):
        detector = detector_fixture
        with patch.object(
            detector, "normalize_email_async", return_value="test@example.com"
        ):
            result = await detector.check_collision("test@example.com")
            assert result is None

    @pytest.mark.asyncio
    async def test_check_collision_with_collision(self, db_setup, detector_fixture):
        detector = detector_fixture
        # Use unique email to avoid conflicts with other tests
        unique_email = f"existing_{id(self)}_{uuid.uuid4().hex}@example.com"
        existing_user = User(
            external_auth_id=f"nextauth_collision_test_{id(self)}_{uuid.uuid4().hex}",
            auth_provider="nextauth",
            email=unique_email,
            normalized_email=unique_email,
        )
        async_session = get_async_session()
        async with async_session() as session:
            session.add(existing_user)
            await session.commit()

            # Patch get_async_session to return a context manager yielding our session
            @contextlib.asynccontextmanager
            async def session_cm():
                yield session

            with patch.object(
                detector, "normalize_email_async", return_value=unique_email
            ):
                with patch(
                    "services.user.utils.email_collision.get_async_session",
                    return_value=session_cm,
                ):
                    result = await detector.check_collision(unique_email)
                    assert result is not None
                    assert result.email == unique_email

    @pytest.mark.asyncio
    async def test_get_collision_details_no_collision(self, db_setup, detector_fixture):
        detector = detector_fixture
        with patch.object(detector, "check_collision", return_value=None):
            with patch.object(
                detector, "normalize_email_async", return_value="test@example.com"
            ):
                result = await detector.get_collision_details("test@example.com")
                assert result["available"] is True
                assert result["collision"] is False
                assert result["normalized_email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_collision_details_with_collision(
        self, db_setup, detector_fixture
    ):
        detector = detector_fixture
        unique_email = f"existing_{id(self)}_{uuid.uuid4().hex}@example.com"
        existing_user = User(
            id=1,
            external_auth_id=f"nextauth_123_{uuid.uuid4().hex}",
            auth_provider="nextauth",
            email=unique_email,
            normalized_email=unique_email,
        )
        with patch.object(detector, "check_collision", return_value=existing_user):
            with patch.object(
                detector, "normalize_email_async", return_value=unique_email
            ):
                result = await detector.get_collision_details(unique_email)
                assert result["collision"] is True
                assert result["existing_user_id"] == existing_user.external_auth_id
                assert result["existing_user_email"] == unique_email
                assert result["normalized_email"] == unique_email

    @pytest.mark.asyncio
    async def test_get_email_info_valid_email(self, db_setup, detector_fixture):
        detector = detector_fixture
        # get_email_info now provides domain extraction instead of provider detection
        result = await detector.get_email_info("user+work@gmail.com")
        assert result["original_email"] == "user+work@gmail.com"
        assert result["normalized_email"] == "user@gmail.com"  # Gmail normalization
        assert result["mailbox_domain"] == "gmail.com"  # Domain extracted from email
        assert result["is_valid"] is True

    @pytest.mark.asyncio
    async def test_get_email_info_invalid_email(self, db_setup, detector_fixture):
        detector = detector_fixture
        # Test the fallback behavior by mocking the simple_email_normalize to fail
        with patch.object(
            detector, "_simple_email_normalize", side_effect=Exception("Invalid email")
        ):
            result = await detector.get_email_info("invalid-email")
            assert result["original_email"] == "invalid-email"
            assert (
                result["normalized_email"] == "invalid-email"
            )  # Falls back to basic strip().lower()
            assert result["mailbox_domain"] == "unknown"
            assert result["is_valid"] is False
            assert "error" in result


# ------------------- Global Instance Test -------------------


class TestEmailCollisionDetectorGlobal:
    def test_global_instance_exists(self):
        assert email_collision_detector is not None
        assert isinstance(email_collision_detector, EmailCollisionDetector)

    @pytest.mark.asyncio
    async def test_global_instance_functionality(self):
        # Global instance should use fast local normalization
        result = await email_collision_detector.normalize_email_async(
            "Test@Example.com"
        )
        assert result == "test@example.com"
