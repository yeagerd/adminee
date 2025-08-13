import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class AuditEventType(Enum):
    """Types of audit events that can be logged"""

    LINK_CREATED = "link_created"
    LINK_UPDATED = "link_updated"
    LINK_DELETED = "link_deleted"
    LINK_TOGGLED = "link_toggled"
    LINK_DUPLICATED = "link_duplicated"
    ONE_TIME_LINK_CREATED = "one_time_link_created"
    BOOKING_CREATED = "booking_created"
    BOOKING_CANCELLED = "booking_cancelled"
    BOOKING_RESCHEDULED = "booking_rescheduled"
    TEMPLATE_CREATED = "template_created"
    TEMPLATE_UPDATED = "template_updated"
    ANALYTICS_VIEWED = "analytics_viewed"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class AuditLogger:
    """Service for logging audit events in the booking system"""

    def __init__(self) -> None:
        # Set up structured logging
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)

        # In production, this would be configured to write to a secure audit log
        # For now, we'll use a basic handler
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        severity: str = "INFO",
    ) -> None:
        """
        Log an audit event

        Args:
            event_type: Type of event being logged
            user_id: ID of the user performing the action
            resource_id: ID of the resource being acted upon
            details: Additional details about the event
            ip_address: IP address of the request
            user_agent: User agent string from the request
            severity: Log level (INFO, WARNING, ERROR)
        """
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "severity": severity,
        }

        # Log the event
        log_message = f"Audit Event: {event_type.value}"
        if user_id:
            log_message += f" | User: {user_id}"
        if resource_id:
            log_message += f" | Resource: {resource_id}"

        if severity == "ERROR":
            self.logger.error(log_message, extra={"audit_data": audit_entry})
        elif severity == "WARNING":
            self.logger.warning(log_message, extra={"audit_data": audit_entry})
        else:
            self.logger.info(log_message, extra={"audit_data": audit_entry})

        # In production, this would also be stored in a secure audit database
        # and potentially sent to a SIEM system

    def log_link_creation(
        self,
        user_id: str,
        link_id: str,
        link_title: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Log the creation of a booking link"""
        self.log_event(
            event_type=AuditEventType.LINK_CREATED,
            user_id=user_id,
            resource_id=link_id,
            details={"link_title": link_title, "action": "created"},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def log_link_update(
        self,
        user_id: str,
        link_id: str,
        changes: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Log updates to a booking link"""
        self.log_event(
            event_type=AuditEventType.LINK_UPDATED,
            user_id=user_id,
            resource_id=link_id,
            details={"changes": changes, "action": "updated"},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def log_link_toggle(
        self,
        user_id: str,
        link_id: str,
        new_status: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Log when a link is enabled/disabled"""
        self.log_event(
            event_type=AuditEventType.LINK_TOGGLED,
            user_id=user_id,
            resource_id=link_id,
            details={"new_status": new_status, "action": "toggled"},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def log_booking_creation(
        self,
        link_id: str,
        booking_id: str,
        attendee_email: str,
        start_time: str,
        end_time: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Log the creation of a booking"""
        # Hash the email for privacy
        from services.meetings.services.security import SecurityUtils

        hashed_email = SecurityUtils.hash_email(attendee_email)

        self.log_event(
            event_type=AuditEventType.BOOKING_CREATED,
            resource_id=link_id,
            details={
                "booking_id": booking_id,
                "attendee_email_hash": hashed_email,
                "start_time": start_time,
                "end_time": end_time,
                "action": "booking_created",
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def log_rate_limit_exceeded(
        self,
        client_key: str,
        endpoint: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Log when rate limits are exceeded"""
        self.log_event(
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
            details={
                "client_key": client_key,
                "endpoint": endpoint,
                "action": "rate_limit_exceeded",
            },
            ip_address=ip_address,
            user_agent=user_agent,
            severity="WARNING",
        )

    def log_suspicious_activity(
        self,
        activity_type: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Log suspicious activity for security monitoring"""
        self.log_event(
            event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
            details={
                "activity_type": activity_type,
                "details": details,
                "action": "suspicious_activity_detected",
            },
            ip_address=ip_address,
            user_agent=user_agent,
            severity="WARNING",
        )


# Global audit logger instance
audit_logger = AuditLogger()


def log_audit_event(
    event_type: AuditEventType,
    user_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    severity: str = "INFO",
) -> None:
    """Convenience function to log audit events"""
    audit_logger.log_event(
        event_type=event_type,
        user_id=user_id,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        severity=severity,
    )
