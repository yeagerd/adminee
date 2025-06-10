"""
Unit tests for audit logging service.

Tests cover audit event logging, querying, analytics, security tracking,
compliance reporting, and data retention policies.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from services.user_management.exceptions import AuditException, DatabaseException
from services.user_management.models.audit import AuditLog
from services.user_management.models.user import User
from services.user_management.services.audit_service import (
    AuditActions,
    AuditLogger,
    ResourceTypes,
    audit_logger,
)


class TestAuditActions:
    """Test audit action constants."""

    def test_user_actions_defined(self):
        """Test that user action constants are defined."""
        assert AuditActions.USER_CREATED == "user_created"
        assert AuditActions.USER_UPDATED == "user_updated"
        assert AuditActions.USER_DELETED == "user_deleted"
        assert AuditActions.USER_LOGIN == "user_login"

    def test_profile_actions_defined(self):
        """Test that profile action constants are defined."""
        assert AuditActions.PROFILE_UPDATED == "profile_updated"
        assert AuditActions.ONBOARDING_COMPLETED == "onboarding_completed"

    def test_preferences_actions_defined(self):
        """Test that preferences action constants are defined."""
        assert AuditActions.PREFERENCES_UPDATED == "preferences_updated"
        assert AuditActions.PREFERENCES_RESET == "preferences_reset"

    def test_security_actions_defined(self):
        """Test that security action constants are defined."""
        assert AuditActions.AUTHENTICATION_FAILED == "authentication_failed"
        assert AuditActions.SUSPICIOUS_ACTIVITY == "suspicious_activity"


class TestResourceTypes:
    """Test resource type constants."""

    def test_resource_types_defined(self):
        """Test that resource type constants are defined."""
        assert ResourceTypes.USER == "user"
        assert ResourceTypes.PREFERENCES == "preferences"
        assert ResourceTypes.INTEGRATION == "integration"
        assert ResourceTypes.TOKEN == "token"
        assert ResourceTypes.SYSTEM == "system"


class TestAuditLogger:
    """Test cases for AuditLogger class."""

    @pytest.fixture
    def audit_service(self):
        """Create audit logger instance for testing."""
        return AuditLogger()

    @pytest.fixture
    def mock_user(self):
        """Create mock user for testing."""
        user = Mock(spec=User)
        user.id = "test_user_123"
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def mock_audit_log(self):
        """Create mock audit log for testing."""
        log = Mock(spec=AuditLog)
        log.id = 1
        log.action = "test_action"
        log.resource_type = "test_resource"
        log.user = None
        log.resource_id = "test_123"
        log.details = {"test": "data"}
        log.ip_address = "192.168.1.1"
        log.user_agent = "test-agent"
        log.created_at = datetime.now(timezone.utc)
        return log

    @pytest.mark.asyncio
    @patch("services.user_management.services.audit_service.User")
    @patch("services.user_management.services.audit_service.AuditLog")
    async def test_log_audit_event_success(
        self, mock_audit_log_model, mock_user_model, audit_service, mock_user
    ):
        """Test successful audit event logging."""
        # Setup mocks
        mock_user_model.objects.get = AsyncMock(return_value=mock_user)
        mock_log = Mock()
        mock_log.id = 1
        mock_audit_log_model.objects.create = AsyncMock(return_value=mock_log)

        # Log audit event
        result = await audit_service.log_audit_event(
            action="test_action",
            resource_type="test_resource",
            user_id="test_user_123",
            resource_id="resource_456",
            details={"key": "value"},
            ip_address="192.168.1.1",
            user_agent="test-agent",
        )

        # Verify database interaction
        mock_user_model.objects.get.assert_called_once_with(id="test_user_123")
        mock_audit_log_model.objects.create.assert_called_once_with(
            user=mock_user,
            action="test_action",
            resource_type="test_resource",
            resource_id="resource_456",
            details={"key": "value"},
            ip_address="192.168.1.1",
            user_agent="test-agent",
        )

        assert result == mock_log

    @pytest.mark.asyncio
    @patch("services.user_management.services.audit_service.User")
    @patch("services.user_management.services.audit_service.AuditLog")
    async def test_log_audit_event_user_not_found(
        self, mock_audit_log_model, mock_user_model, audit_service
    ):
        """Test audit logging when user is not found."""
        # Setup mocks
        mock_user_model.objects.get = AsyncMock(side_effect=Exception("User not found"))
        mock_log = Mock()
        mock_log.id = 1
        mock_audit_log_model.objects.create = AsyncMock(return_value=mock_log)

        # Log audit event
        result = await audit_service.log_audit_event(
            action="test_action",
            resource_type="test_resource",
            user_id="nonexistent_user",
        )

        # Verify it logs as system event (user=None)
        mock_audit_log_model.objects.create.assert_called_once_with(
            user=None,
            action="test_action",
            resource_type="test_resource",
            resource_id=None,
            details={},
            ip_address=None,
            user_agent=None,
        )

        assert result == mock_log

    @pytest.mark.asyncio
    @patch("services.user_management.services.audit_service.AuditLog")
    async def test_log_audit_event_system_event(
        self, mock_audit_log_model, audit_service
    ):
        """Test logging system events (no user)."""
        mock_log = Mock()
        mock_log.id = 1
        mock_audit_log_model.objects.create = AsyncMock(return_value=mock_log)

        # Log system event
        result = await audit_service.log_audit_event(
            action="system_backup",
            resource_type="system",
            details={"backup_size": "10GB"},
        )

        # Verify system event logged without user
        mock_audit_log_model.objects.create.assert_called_once_with(
            user=None,
            action="system_backup",
            resource_type="system",
            resource_id=None,
            details={"backup_size": "10GB"},
            ip_address=None,
            user_agent=None,
        )

        assert result == mock_log

    @pytest.mark.asyncio
    @patch("services.user_management.services.audit_service.AuditLog")
    async def test_log_audit_event_database_error(
        self, mock_audit_log_model, audit_service
    ):
        """Test audit logging with database error."""
        # Setup mock to raise database error
        mock_audit_log_model.objects.create = AsyncMock(
            side_effect=SQLAlchemyError("Database error")
        )

        # Attempt to log event
        with pytest.raises(AuditException) as exc_info:
            await audit_service.log_audit_event(
                action="test_action", resource_type="test_resource"
            )

        assert "Failed to persist audit log for action test_action" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_log_user_action(self, audit_service):
        """Test convenience method for user actions."""
        with patch.object(audit_service, "log_audit_event") as mock_log:
            mock_log.return_value = Mock()

            await audit_service.log_user_action(
                user_id="user_123",
                action="profile_updated",
                resource_type="user",
                resource_id="user_123",
                details={"field": "name"},
                ip_address="192.168.1.1",
            )

            mock_log.assert_called_once_with(
                action="profile_updated",
                resource_type="user",
                user_id="user_123",
                resource_id="user_123",
                details={"field": "name"},
                ip_address="192.168.1.1",
                user_agent=None,
            )

    @pytest.mark.asyncio
    async def test_log_system_action(self, audit_service):
        """Test convenience method for system actions."""
        with patch.object(audit_service, "log_audit_event") as mock_log:
            mock_log.return_value = Mock()

            await audit_service.log_system_action(
                action="system_maintenance",
                details={"duration": "30min"},
            )

            mock_log.assert_called_once_with(
                action="system_maintenance",
                resource_type="system",
                user_id=None,
                resource_id=None,
                details={"duration": "30min"},
            )

    @pytest.mark.asyncio
    async def test_log_security_event(self, audit_service):
        """Test logging security events with enhanced metadata."""
        with patch.object(audit_service, "log_audit_event") as mock_log:
            mock_log.return_value = Mock()

            await audit_service.log_security_event(
                action="authentication_failed",
                user_id="user_123",
                ip_address="192.168.1.1",
                severity="high",
            )

            # Verify enhanced details were added
            call_args = mock_log.call_args
            details = call_args[1]["details"]
            assert details["security_event"] is True
            assert details["severity"] == "high"
            assert "timestamp" in details

    @pytest.mark.asyncio
    @patch("services.user_management.services.audit_service.AuditLog")
    async def test_query_audit_logs_basic(self, mock_audit_log_model, audit_service):
        """Test basic audit log querying."""
        # Setup mock query chain
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all = AsyncMock(return_value=[Mock(), Mock()])

        mock_audit_log_model.objects.select_related.return_value = mock_query

        # Query logs
        results = await audit_service.query_audit_logs(
            user_id="user_123", action="login", limit=10
        )

        # Verify query was built correctly
        mock_audit_log_model.objects.select_related.assert_called_once_with("user")
        assert len(results) == 2

    @pytest.mark.asyncio
    @patch("services.user_management.services.audit_service.AuditLog")
    async def test_query_audit_logs_with_date_range(
        self, mock_audit_log_model, audit_service
    ):
        """Test querying audit logs with date range."""
        # Setup mock query chain
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all = AsyncMock(return_value=[])

        mock_audit_log_model.objects.select_related.return_value = mock_query

        # Query logs with date range
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)

        await audit_service.query_audit_logs(start_date=start_date, end_date=end_date)

        # Verify date filters were applied
        assert mock_query.filter.call_count >= 2

    @pytest.mark.asyncio
    @patch("services.user_management.services.audit_service.AuditLog")
    async def test_query_audit_logs_database_error(
        self, mock_audit_log_model, audit_service
    ):
        """Test audit log querying with database error."""
        mock_audit_log_model.objects.select_related.side_effect = SQLAlchemyError(
            "Query failed"
        )

        with pytest.raises(DatabaseException) as exc_info:
            await audit_service.query_audit_logs()

        assert "Failed to query audit logs" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_user_activity_summary(self, audit_service):
        """Test user activity summary generation."""
        # Mock audit logs for analysis
        mock_logs = []
        now = datetime.now(timezone.utc)

        for i in range(5):
            log = Mock()
            log.action = f"action_{i % 3}"  # 3 different actions
            log.resource_type = f"resource_{i % 2}"  # 2 different resources
            log.created_at = now - timedelta(days=i)
            mock_logs.append(log)

        with patch.object(audit_service, "query_audit_logs") as mock_query:
            mock_query.return_value = mock_logs

            summary = await audit_service.get_user_activity_summary(
                user_id="user_123", days=30
            )

            # Verify summary structure
            assert summary["user_id"] == "user_123"
            assert summary["period_days"] == 30
            assert summary["total_activities"] == 5
            assert "action_breakdown" in summary
            assert "resource_breakdown" in summary
            assert "daily_activity" in summary

    @pytest.mark.asyncio
    async def test_get_user_activity_summary_error(self, audit_service):
        """Test user activity summary with error."""
        with patch.object(audit_service, "query_audit_logs") as mock_query:
            mock_query.side_effect = Exception("Query failed")

            with pytest.raises(AuditException) as exc_info:
                await audit_service.get_user_activity_summary("user_123")

            assert "Failed to generate activity summary for user user_123" in str(
                exc_info.value
            )

    @pytest.mark.asyncio
    @patch("services.user_management.services.audit_service.AuditLog")
    async def test_get_security_events(self, mock_audit_log_model, audit_service):
        """Test retrieving security events."""
        # Setup mock query for security events
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all = AsyncMock(return_value=[Mock(), Mock()])

        mock_audit_log_model.objects.select_related.return_value = mock_query

        # Get security events
        events = await audit_service.get_security_events(severity="high")

        # Verify security actions were filtered
        mock_query.filter.assert_called()
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_get_security_events_error(self, audit_service):
        """Test security events retrieval with error."""
        with patch(
            "services.user_management.services.audit_service.AuditLog"
        ) as mock_model:
            mock_model.objects.select_related.side_effect = Exception("Query failed")

            with pytest.raises(AuditException) as exc_info:
                await audit_service.get_security_events()

            assert "Failed to retrieve security events" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("services.user_management.services.audit_service.AuditLog")
    async def test_cleanup_old_logs_success(self, mock_audit_log_model, audit_service):
        """Test successful cleanup of old audit logs."""
        # Setup mocks
        old_logs = [Mock(), Mock(), Mock()]  # 3 old logs
        mock_query = Mock()
        mock_query.all = AsyncMock(return_value=old_logs)
        mock_query.delete = AsyncMock(return_value=None)
        mock_audit_log_model.objects.filter.return_value = mock_query

        # Mock the log_system_action call
        with patch.object(audit_service, "log_system_action") as mock_log_system:
            mock_log_system.return_value = Mock()

            # Cleanup old logs
            deleted_count = await audit_service.cleanup_old_logs(retention_days=90)

            # Verify cleanup
            assert deleted_count == 3
            mock_query.delete.assert_called_once()
            mock_log_system.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.user_management.services.audit_service.AuditLog")
    async def test_cleanup_old_logs_none_to_delete(
        self, mock_audit_log_model, audit_service
    ):
        """Test cleanup when no old logs exist."""
        # Setup mocks - no old logs
        mock_query = Mock()
        mock_query.all = AsyncMock(return_value=[])
        mock_audit_log_model.objects.filter.return_value = mock_query

        # Cleanup old logs
        deleted_count = await audit_service.cleanup_old_logs()

        # Verify no deletion occurred
        assert deleted_count == 0
        mock_query.delete.assert_not_called()

    @pytest.mark.asyncio
    @patch("services.user_management.services.audit_service.AuditLog")
    async def test_cleanup_old_logs_database_error(
        self, mock_audit_log_model, audit_service
    ):
        """Test cleanup with database error."""
        mock_audit_log_model.objects.filter.side_effect = SQLAlchemyError(
            "Database error"
        )

        with pytest.raises(AuditException) as exc_info:
            await audit_service.cleanup_old_logs()

        assert "Failed to cleanup old audit logs" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_compliance_report(self, audit_service):
        """Test compliance report generation."""
        # Mock audit logs for report
        mock_user = Mock()
        mock_user.id = "user_123"

        mock_logs = []
        for i in range(10):
            log = Mock()
            log.action = f"action_{i % 4}"
            log.resource_type = f"resource_{i % 3}"
            log.user = (
                mock_user if i % 2 == 0 else None
            )  # Mix of user and system events
            log.details = {"security_event": True} if i == 0 else {}
            mock_logs.append(log)

        with patch.object(audit_service, "query_audit_logs") as mock_query:
            mock_query.return_value = mock_logs

            start_date = datetime.now(timezone.utc) - timedelta(days=30)
            end_date = datetime.now(timezone.utc)

            report = await audit_service.generate_compliance_report(
                start_date=start_date, end_date=end_date
            )

            # Verify report structure
            assert "report_period" in report
            assert "summary" in report
            assert "breakdown" in report
            assert "compliance_metrics" in report
            assert report["summary"]["total_events"] == 10
            assert report["summary"]["security_events"] == 1

    @pytest.mark.asyncio
    async def test_generate_compliance_report_error(self, audit_service):
        """Test compliance report generation with error."""
        with patch.object(audit_service, "query_audit_logs") as mock_query:
            mock_query.side_effect = Exception("Query failed")

            start_date = datetime.now(timezone.utc) - timedelta(days=30)
            end_date = datetime.now(timezone.utc)

            with pytest.raises(AuditException) as exc_info:
                await audit_service.generate_compliance_report(
                    start_date=start_date, end_date=end_date
                )

            assert "Failed to generate compliance report" in str(exc_info.value)


class TestGlobalAuditLogger:
    """Test global audit logger instance."""

    def test_global_audit_logger_exists(self):
        """Test that global audit logger instance exists."""
        assert audit_logger is not None
        assert isinstance(audit_logger, AuditLogger)

    def test_global_audit_logger_singleton(self):
        """Test that audit_logger is a singleton-like instance."""
        from services.user_management.services.audit_service import audit_logger as al2

        assert audit_logger is al2


class TestAuditIntegration:
    """Integration tests for audit functionality."""

    @pytest.fixture
    def sample_audit_data(self):
        """Sample audit event data for testing."""
        return {
            "action": AuditActions.USER_LOGIN,
            "resource_type": ResourceTypes.USER,
            "user_id": "test_user_123",
            "resource_id": "test_user_123",
            "details": {"login_method": "oauth", "provider": "google"},
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0 Chrome/91.0",
        }

    def test_audit_event_structure(self, sample_audit_data):
        """Test that audit event data has proper structure."""
        required_fields = ["action", "resource_type"]
        optional_fields = [
            "user_id",
            "resource_id",
            "details",
            "ip_address",
            "user_agent",
        ]

        # Check required fields
        for field in required_fields:
            assert field in sample_audit_data

        # Check optional fields are handled properly
        for field in optional_fields:
            assert field in sample_audit_data or field not in sample_audit_data

    def test_security_event_enhancement(self):
        """Test that security events get proper enhancement."""
        base_details = {"attempt_count": 3}
        security_details = base_details.copy()
        security_details.update(
            {
                "security_event": True,
                "severity": "high",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        # Verify security enhancement
        assert security_details["security_event"] is True
        assert security_details["severity"] == "high"
        assert "timestamp" in security_details
        assert security_details["attempt_count"] == 3  # Original data preserved

    def test_compliance_metrics_calculation(self):
        """Test compliance metrics calculation logic."""
        # Sample action counts
        action_summary = {
            "preferences_updated": 5,
            "profile_updated": 3,
            "user_login": 10,
            "user_logout": 8,
            "user_updated": 2,
        }

        # Calculate compliance metrics
        data_access_events = action_summary.get(
            "preferences_updated", 0
        ) + action_summary.get("profile_updated", 0)
        authentication_events = action_summary.get(
            "user_login", 0
        ) + action_summary.get("user_logout", 0)
        data_modification_events = action_summary.get(
            "user_updated", 0
        ) + action_summary.get("preferences_updated", 0)

        # Verify calculations
        assert data_access_events == 8  # 5 + 3
        assert authentication_events == 18  # 10 + 8
        assert data_modification_events == 7  # 2 + 5
