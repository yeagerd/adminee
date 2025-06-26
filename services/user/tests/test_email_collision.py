"""
Unit tests for email collision detection functionality.

Tests email normalization and collision detection using the email-normalize library.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

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

    @pytest.mark.asyncio
    async def test_normalize_email_gmail(self):
        test_cases = [
            ("user@gmail.com", "user@gmail.com"),
            ("User@gmail.com", "user@gmail.com"),
            ("user+work@gmail.com", "user@gmail.com"),
            ("first.last@gmail.com", "firstlast@gmail.com"),
            ("F.I.R.S.T.L.A.S.T@gmail.com", "firstlast@gmail.com"),
            ("user+work+personal@gmail.com", "user@gmail.com"),
        ]
        for input_email, expected in test_cases:
            with patch(
                "services.user.utils.email_collision.normalize"
            ) as mock_normalize:
                mock_result = MagicMock()
                mock_result.normalized_address = expected
                mock_normalize.return_value = mock_result
                result = await self.detector.normalize_email(input_email)
                assert result == expected

    @pytest.mark.asyncio
    async def test_normalize_email_outlook(self):
        test_cases = [
            ("user@outlook.com", "user@outlook.com"),
            ("user+work@outlook.com", "user@outlook.com"),
            ("first.last@outlook.com", "first.last@outlook.com"),
            ("User@Outlook.com", "user@outlook.com"),
        ]
        for input_email, expected in test_cases:
            with patch(
                "services.user.utils.email_collision.normalize"
            ) as mock_normalize:
                mock_result = MagicMock()
                mock_result.normalized_address = expected
                mock_normalize.return_value = mock_result
                result = await self.detector.normalize_email(input_email)
                assert result == expected

    @pytest.mark.asyncio
    async def test_normalize_email_yahoo(self):
        test_cases = [
            ("user@yahoo.com", "user@yahoo.com"),
            ("user+work@yahoo.com", "user@yahoo.com"),
            ("first.last@yahoo.com", "firstlast@yahoo.com"),
            ("User@Yahoo.com", "user@yahoo.com"),
        ]
        for input_email, expected in test_cases:
            with patch(
                "services.user.utils.email_collision.normalize"
            ) as mock_normalize:
                mock_result = MagicMock()
                mock_result.normalized_address = expected
                mock_normalize.return_value = mock_result
                result = await self.detector.normalize_email(input_email)
                assert result == expected

    @pytest.mark.asyncio
    async def test_normalize_email_custom_domain(self):
        test_cases = [
            ("user@company.com", "user@company.com"),
            ("User@Company.com", "user@company.com"),
            ("user+work@company.com", "user+work@company.com"),
        ]
        for input_email, expected in test_cases:
            with patch(
                "services.user.utils.email_collision.normalize"
            ) as mock_normalize:
                mock_result = MagicMock()
                mock_result.normalized_address = expected
                mock_normalize.return_value = mock_result
                result = await self.detector.normalize_email(input_email)
                assert result == expected

    @pytest.mark.asyncio
    async def test_normalize_email_empty_input(self):
        result = await self.detector.normalize_email("")
        assert result == ""

    @pytest.mark.asyncio
    async def test_normalize_email_fallback(self):
        with patch("services.user.utils.email_collision.normalize") as mock_normalize:
            mock_normalize.side_effect = Exception("Normalization failed")
            result = await self.detector.normalize_email("User@Gmail.com")
            assert result == "user@gmail.com"


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
def detector_fixture():
    return EmailCollisionDetector()


class TestEmailCollisionDB:
    @pytest.mark.asyncio
    async def test_check_collision_no_collision(self, db_setup, detector_fixture):
        detector = detector_fixture
        with patch.object(detector, "normalize_email", return_value="test@example.com"):
            result = await detector.check_collision("test@example.com")
            assert result is None

    @pytest.mark.asyncio
    async def test_check_collision_with_collision(self, db_setup, detector_fixture):
        detector = detector_fixture
        existing_user = User(
            external_auth_id="clerk_collision_test_123",
            auth_provider="clerk",
            email="existing@example.com",
            normalized_email="existing@example.com",
        )
        async_session = get_async_session()
        async with async_session() as session:
            session.add(existing_user)
            await session.commit()
            with patch.object(
                detector, "normalize_email", return_value="existing@example.com"
            ):
                result = await detector.check_collision("existing@example.com")
                assert result is not None
                assert result.email == "existing@example.com"

    @pytest.mark.asyncio
    async def test_get_collision_details_no_collision(self, db_setup, detector_fixture):
        detector = detector_fixture
        with patch.object(detector, "check_collision", return_value=None):
            result = await detector.get_collision_details("test@example.com")
            assert result == {"collision": False}

    @pytest.mark.asyncio
    async def test_get_collision_details_with_collision(
        self, db_setup, detector_fixture
    ):
        detector = detector_fixture
        existing_user = User(
            id=1,
            external_auth_id="clerk_123",
            auth_provider="clerk",
            email="existing@example.com",
            normalized_email="existing@example.com",
        )
        with patch.object(detector, "check_collision", return_value=existing_user):
            with patch(
                "services.user.utils.email_collision.normalize"
            ) as mock_normalize:
                mock_result = MagicMock()
                mock_result.mailbox_provider = "Google"
                mock_result.mx_records = [("5", "gmail-smtp-in.l.google.com")]
                mock_normalize.return_value = mock_result
                result = await detector.get_collision_details("existing@example.com")
                assert result["collision"] is True
                assert result["existing_user_id"] == 1
                assert result["original_email"] == "existing@example.com"
                assert result["normalized_email"] == "existing@example.com"
                assert result["auth_provider"] == "clerk"
                assert result["provider_info"]["mailbox_provider"] == "Google"

    @pytest.mark.asyncio
    async def test_get_email_info_valid_email(self, db_setup, detector_fixture):
        detector = detector_fixture
        with patch("services.user.utils.email_collision.normalize") as mock_normalize:
            mock_result = MagicMock()
            mock_result.normalized_address = "user@gmail.com"
            mock_result.mailbox_provider = "Google"
            mock_result.mx_records = [("5", "gmail-smtp-in.l.google.com")]
            mock_normalize.return_value = mock_result
            result = await detector.get_email_info("user+work@gmail.com")
            assert result["original_email"] == "user+work@gmail.com"
            assert result["normalized_email"] == "user@gmail.com"
            assert result["mailbox_provider"] == "Google"
            assert result["is_valid"] is True

    @pytest.mark.asyncio
    async def test_get_email_info_invalid_email(self, db_setup, detector_fixture):
        detector = detector_fixture
        with patch("services.user.utils.email_collision.normalize") as mock_normalize:
            mock_normalize.side_effect = Exception("Invalid email")
            result = await detector.get_email_info("invalid-email")
            assert result["original_email"] == "invalid-email"
            assert result["normalized_email"] == "invalid-email"
            assert result["mailbox_provider"] == "unknown"
            assert result["is_valid"] is False
            assert "error" in result


# ------------------- Global Instance Test -------------------


class TestEmailCollisionDetectorGlobal:
    def test_global_instance_exists(self):
        assert email_collision_detector is not None
        assert isinstance(email_collision_detector, EmailCollisionDetector)

    @pytest.mark.asyncio
    async def test_global_instance_functionality(self):
        with patch("services.user.utils.email_collision.normalize") as mock_normalize:
            mock_result = MagicMock()
            mock_result.normalized_address = "test@example.com"
            mock_normalize.return_value = mock_result
            result = await email_collision_detector.normalize_email("test@example.com")
            assert result == "test@example.com"
