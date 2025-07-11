"""
Audit logging service for User Management Service.

Provides comprehensive audit logging for compliance, security tracking,
and operational monitoring with database persistence and analytics.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select

from services.user.database import get_async_session
from services.user.models.audit import AuditLog
from services.user.models.user import User

# Set up logging
logger = structlog.get_logger(__name__)


# Audit action constants
class AuditActions:
    """Standard audit action constants for consistency."""

    # User actions
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_PASSWORD_CHANGED = "user_password_changed"

    # Profile actions
    PROFILE_UPDATED = "profile_updated"
    PROFILE_IMAGE_UPDATED = "profile_image_updated"
    ONBOARDING_COMPLETED = "onboarding_completed"
    ONBOARDING_STEP_UPDATED = "onboarding_step_updated"

    # Preferences actions
    PREFERENCES_UPDATED = "preferences_updated"
    PREFERENCES_RESET = "preferences_reset"
    PREFERENCES_EXPORTED = "preferences_exported"
    PREFERENCES_IMPORTED = "preferences_imported"

    # Integration actions
    INTEGRATION_CONNECTED = "integration_connected"
    INTEGRATION_DISCONNECTED = "integration_disconnected"
    INTEGRATION_REFRESHED = "integration_refreshed"
    INTEGRATION_ERROR = "integration_error"

    # Token actions
    TOKEN_CREATED = "token_created"
    TOKEN_REFRESHED = "token_refreshed"
    TOKEN_REVOKED = "token_revoked"
    TOKEN_ENCRYPTED = "token_encrypted"
    TOKEN_DECRYPTED = "token_decrypted"
    TOKEN_ROTATION = "token_rotation"

    # Security actions
    AUTHENTICATION_FAILED = "authentication_failed"
    AUTHORIZATION_FAILED = "authorization_failed"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    DATA_BREACH_DETECTED = "data_breach_detected"

    # System actions
    SYSTEM_BACKUP = "system_backup"
    SYSTEM_MAINTENANCE = "system_maintenance"
    SYSTEM_UPGRADE = "system_upgrade"
    DATA_CLEANUP = "data_cleanup"


class ResourceTypes:
    """Standard resource type constants for consistency."""

    USER = "user"
    PREFERENCES = "preferences"
    INTEGRATION = "integration"
    TOKEN = "token"
    SYSTEM = "system"
    WEBHOOK = "webhook"
    API_KEY = "api_key"


class AuditLogger:
    """
    Comprehensive audit logging service.

    Features:
    - Structured logging with database persistence
    - User activity tracking and security monitoring
    - Compliance reporting and analytics
    - Automatic retention and cleanup
    - Query and filtering capabilities
    """

    def __init__(self):
        """Initialize the audit logger."""
        self.logger = structlog.get_logger(__name__)

    async def log_audit_event(
        self,
        action: str,
        resource_type: str,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Log an audit event to both structured logs and database.

        Args:
            action: The action being performed (use AuditActions constants)
            resource_type: Type of resource (use ResourceTypes constants)
            user_id: ID of user performing action (None for system events)
            resource_id: ID of specific resource being acted upon
            details: Additional structured details about the action
            ip_address: IP address of the request
            user_agent: User agent string from request

        Returns:
            Created AuditLog record

        Raises:
            Exception: If audit logging fails
        """
        try:
            self.logger.info(
                "audit_event",
                action=action,
                resource_type=resource_type,
                user_id=user_id,
                resource_id=resource_id,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent,
            )

            # Get user object if user_id provided
            user = None
            if user_id:
                try:
                    async_session = get_async_session()
                    async with async_session() as session:
                        # Handle both internal ID and external auth ID
                        if user_id.isdigit():
                            # Numeric user ID - internal database ID
                            result = await session.execute(
                                select(User).where(User.id == int(user_id))
                            )
                        else:
                            # String user ID - external auth ID
                            result = await session.execute(
                                select(User).where(User.external_auth_id == user_id)
                            )
                        user = result.scalar_one_or_none()
                except Exception:
                    # User might be deleted, log as system event
                    self.logger.warning(
                        "audit_user_not_found",
                        user_id=user_id,
                        action=action,
                    )

            # Create database audit log using async session
            async_session = get_async_session()
            async with async_session() as session:
                audit_log = AuditLog(
                    user_id=user.id if user else None,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details=details or {},
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                session.add(audit_log)
                await session.commit()
                await session.refresh(audit_log)

            self.logger.debug(
                "audit_event_persisted",
                audit_id=audit_log.id,
                action=action,
                user_id=user_id,
            )

            return audit_log

        except SQLAlchemyError as e:
            self.logger.error(
                "audit_database_error",
                error=str(e),
                action=action,
                user_id=user_id,
            )
            raise Exception(
                f"Failed to persist audit log for action {action}",
                {"action": action, "user_id": user_id, "error": str(e)},
            )
        except Exception as e:
            self.logger.error(
                "audit_unexpected_error",
                error=str(e),
                action=action,
                user_id=user_id,
            )
            raise Exception(
                f"Unexpected error during audit logging for action {action}",
                {"action": action, "user_id": user_id, "error": str(e)},
            )

    async def log_user_action(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Convenience method for logging user-specific actions.

        Args:
            user_id: ID of user performing action
            action: The action being performed
            resource_type: Type of resource being acted upon
            resource_id: ID of specific resource
            details: Additional details about the action
            ip_address: IP address of the request
            user_agent: User agent string

        Returns:
            Created AuditLog record
        """
        return await self.log_audit_event(
            action=action,
            resource_type=resource_type,
            user_id=user_id,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_system_action(
        self,
        action: str,
        resource_type: str = ResourceTypes.SYSTEM,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """
        Convenience method for logging system actions (no user).

        Args:
            action: The action being performed
            resource_type: Type of resource (defaults to system)
            resource_id: ID of specific resource
            details: Additional details about the action

        Returns:
            Created AuditLog record
        """
        return await self.log_audit_event(
            action=action,
            resource_type=resource_type,
            user_id=None,
            resource_id=resource_id,
            details=details,
        )

    async def log_security_event(
        self,
        action: str,
        user_id: Optional[str] = None,
        resource_type: str = ResourceTypes.SYSTEM,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        severity: str = "medium",
    ) -> AuditLog:
        """
        Log security-related events with enhanced details.

        Args:
            action: Security action being logged
            user_id: User involved (if any)
            resource_type: Type of resource
            resource_id: ID of specific resource
            details: Additional security details
            ip_address: IP address involved
            user_agent: User agent string
            severity: Security severity level (low, medium, high, critical)

        Returns:
            Created AuditLog record
        """
        # Enhance details with security metadata
        security_details = details or {}
        security_details.update(
            {
                "security_event": True,
                "severity": severity,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        # Log with higher priority for security events
        self.logger.warning(
            "security_audit_event",
            action=action,
            user_id=user_id,
            severity=severity,
            ip_address=ip_address,
        )

        return await self.log_audit_event(
            action=action,
            resource_type=resource_type,
            user_id=user_id,
            resource_id=resource_id,
            details=security_details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def query_audit_logs(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """
        Query audit logs with filtering and pagination.

        Args:
            user_id: Filter by user ID
            action: Filter by action type
            resource_type: Filter by resource type
            resource_id: Filter by specific resource ID
            start_date: Filter logs after this date
            end_date: Filter logs before this date
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching AuditLog records

        Raises:
            Exception: If query fails
        """
        try:
            async_session = get_async_session()
            async with async_session() as session:
                query = select(AuditLog)

                # Apply filters
                if user_id:
                    if user_id.isdigit():
                        query = query.where(AuditLog.user_id == int(user_id))
                    else:
                        # Join with user table for external auth ID lookup
                        query = query.join(User).where(User.external_auth_id == user_id)
                if action:
                    query = query.where(AuditLog.action == action)
                if resource_type:
                    query = query.where(AuditLog.resource_type == resource_type)
                if resource_id:
                    query = query.where(AuditLog.resource_id == resource_id)
                if start_date:
                    query = query.where(AuditLog.created_at >= start_date)
                if end_date:
                    query = query.where(AuditLog.created_at <= end_date)

                # Order by most recent first and apply pagination
                query = (
                    query.order_by(AuditLog.created_at.desc())  # type: ignore[attr-defined]
                    .offset(offset)
                    .limit(limit)
                )

                result = await session.execute(query)
                audit_logs = list(result.scalars().all())

            self.logger.debug(
                "audit_query_executed",
                filters={
                    "user_id": user_id,
                    "action": action,
                    "resource_type": resource_type,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                },
                result_count=len(audit_logs),
            )

            return audit_logs

        except SQLAlchemyError as e:
            self.logger.error("audit_query_failed", error=str(e))
            raise Exception(
                "Failed to query audit logs",
                {"error": str(e)},
            )

    async def get_user_activity_summary(
        self,
        user_id: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get activity summary for a specific user.

        Args:
            user_id: User ID to analyze
            days: Number of days to analyze (default 30)

        Returns:
            Dictionary with activity metrics and patterns
        """
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Get all user activities in the time period
            activities = await self.query_audit_logs(
                user_id=user_id,
                start_date=start_date,
                limit=1000,  # Large limit for comprehensive analysis
            )

            # Analyze activity patterns
            action_counts: Dict[str, int] = {}
            resource_counts: Dict[str, int] = {}
            daily_counts: Dict[str, int] = {}

            for activity in activities:
                # Count by action
                action_counts[activity.action] = (
                    action_counts.get(activity.action, 0) + 1
                )

                # Count by resource type
                resource_counts[activity.resource_type] = (
                    resource_counts.get(activity.resource_type, 0) + 1
                )

                # Count by day
                day_key = activity.created_at.date().isoformat()
                daily_counts[day_key] = daily_counts.get(day_key, 0) + 1

            summary = {
                "user_id": user_id,
                "period_days": days,
                "total_activities": len(activities),
                "action_breakdown": action_counts,
                "resource_breakdown": resource_counts,
                "daily_activity": daily_counts,
                "most_active_day": (
                    max(daily_counts.items(), key=lambda x: x[1])
                    if daily_counts
                    else None
                ),
                "most_common_action": (
                    max(action_counts.items(), key=lambda x: x[1])
                    if action_counts
                    else None
                ),
            }

            self.logger.info(
                "user_activity_summary_generated",
                user_id=user_id,
                total_activities=len(activities),
                period_days=days,
            )

            return summary

        except Exception as e:
            self.logger.error(
                "activity_summary_failed",
                user_id=user_id,
                error=str(e),
            )
            from services.common.http_errors import ServiceError

            raise ServiceError(
                message=f"Failed to generate activity summary for user {user_id}: {str(e)}",
                details={"user_id": user_id, "error": str(e)},
            )

    async def get_security_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        """
        Get security-related audit events for monitoring.

        Args:
            start_date: Filter events after this date
            end_date: Filter events before this date
            severity: Filter by severity level
            limit: Maximum number of results

        Returns:
            List of security-related AuditLog records
        """
        try:
            async_session = get_async_session()
            async with async_session() as session:
                query = select(AuditLog)

                # Filter for security events
                security_actions = [
                    AuditActions.AUTHENTICATION_FAILED,
                    AuditActions.AUTHORIZATION_FAILED,
                    AuditActions.SUSPICIOUS_ACTIVITY,
                    AuditActions.DATA_BREACH_DETECTED,
                    AuditActions.TOKEN_DECRYPTED,
                    AuditActions.TOKEN_ROTATION,
                ]

                query = query.where(AuditLog.action.in_(security_actions))  # type: ignore[attr-defined]

                # Apply date filters
                if start_date:
                    query = query.where(AuditLog.created_at >= start_date)
                if end_date:
                    query = query.where(AuditLog.created_at <= end_date)

                # Filter by severity if specified
                if severity:
                    # Note: JSON filtering might need adjustment based on database
                    query = query.where(AuditLog.details["severity"].astext == severity)  # type: ignore[index]

                query = query.order_by(AuditLog.created_at.desc()).limit(limit)  # type: ignore[attr-defined]
                result = await session.execute(query)
                security_events = list(result.scalars().all())

            self.logger.info(
                "security_events_retrieved",
                count=len(security_events),
                severity=severity,
            )

            return security_events

        except Exception as e:
            self.logger.error("security_events_query_failed", error=str(e))
            raise Exception(
                "Failed to retrieve security events",
                {"error": str(e)},
            )

    async def cleanup_old_logs(self, retention_days: int = 365) -> int:
        """
        Clean up old audit logs based on retention policy.

        Args:
            retention_days: Number of days to retain logs

        Returns:
            Number of logs deleted

        Raises:
            Exception: If cleanup fails
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

            async_session = get_async_session()
            async with async_session() as session:
                # Get count before deletion for reporting
                count_query = select(AuditLog).where(AuditLog.created_at < cutoff_date)
                result = await session.execute(count_query)
                old_logs = list(result.scalars().all())
                count_to_delete = len(old_logs)

                if count_to_delete == 0:
                    self.logger.info(
                        "audit_cleanup_no_logs_to_delete", retention_days=retention_days
                    )
                    return 0

                # Delete old logs
                for log in old_logs:
                    await session.delete(log)
                await session.commit()

            # Log the cleanup action
            await self.log_system_action(
                action=AuditActions.DATA_CLEANUP,
                details={
                    "cleanup_type": "audit_logs",
                    "retention_days": retention_days,
                    "logs_deleted": count_to_delete,
                    "cutoff_date": cutoff_date.isoformat(),
                },
            )

            self.logger.info(
                "audit_logs_cleaned_up",
                logs_deleted=count_to_delete,
                retention_days=retention_days,
            )

            return count_to_delete

        except SQLAlchemyError as e:
            self.logger.error("audit_cleanup_failed", error=str(e))
            raise Exception(
                "Failed to cleanup old audit logs",
                {"retention_days": retention_days, "error": str(e)},
            )

    async def generate_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate compliance report for audit logs in date range.

        Args:
            start_date: Report start date
            end_date: Report end date
            user_id: Optional user ID to filter by

        Returns:
            Comprehensive compliance report
        """
        try:
            # Get all audit logs in the period
            logs = await self.query_audit_logs(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                limit=10000,  # Large limit for comprehensive report
            )

            # Analyze the logs
            total_events = len(logs)
            unique_users = len(set(log.user.id for log in logs if log.user))

            # Categorize events by type
            user_events = [log for log in logs if log.user]
            system_events = [log for log in logs if not log.user]
            security_events = [
                log for log in logs if log.details and log.details.get("security_event")
            ]

            # Count by action and resource type
            action_summary: Dict[str, int] = {}
            resource_summary: Dict[str, int] = {}

            for log in logs:
                action_summary[log.action] = action_summary.get(log.action, 0) + 1
                resource_summary[log.resource_type] = (
                    resource_summary.get(log.resource_type, 0) + 1
                )

            report = {
                "report_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "duration_days": (end_date - start_date).days,
                },
                "summary": {
                    "total_events": total_events,
                    "user_events": len(user_events),
                    "system_events": len(system_events),
                    "security_events": len(security_events),
                    "unique_users_active": unique_users,
                },
                "breakdown": {
                    "by_action": action_summary,
                    "by_resource_type": resource_summary,
                },
                "compliance_metrics": {
                    "data_access_events": action_summary.get("preferences_updated", 0)
                    + action_summary.get("profile_updated", 0),
                    "authentication_events": action_summary.get("user_login", 0)
                    + action_summary.get("user_logout", 0),
                    "data_modification_events": action_summary.get("user_updated", 0)
                    + action_summary.get("preferences_updated", 0),
                    "security_incidents": len(security_events),
                },
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "generated_for_user": user_id,
            }

            self.logger.info(
                "compliance_report_generated",
                total_events=total_events,
                period_days=(end_date - start_date).days,
                user_id=user_id,
            )

            return report

        except Exception as e:
            self.logger.error(
                "compliance_report_failed",
                error=str(e),
                user_id=user_id,
            )
            from services.common.http_errors import ServiceError

            raise ServiceError(
                message=f"Failed to generate compliance report: {str(e)}",
                details={"user_id": user_id, "error": str(e)},
            )


# Global audit logger instance
audit_logger = AuditLogger()
