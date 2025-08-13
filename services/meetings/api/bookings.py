from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from services.meetings.models.bookings import (
    BookingLink,
    OneTimeLink,
    BookingTemplate,
    Booking,
    AnalyticsEvent,
)
from services.meetings.services.booking_availability import get_booking_availability
from services.meetings.services.booking_events import create_booking_calendar_event
from services.meetings.services.contacts_integration import search_contacts, create_contact
from services.meetings.services.booking_emails import send_confirmation_email, send_follow_up_email
from services.meetings.services.security import (
    TokenGenerator,
    SecurityUtils,
    check_rate_limit,
    get_remaining_requests
)
from services.meetings.services.audit_logger import (
    audit_logger,
    AuditEventType
)

router = APIRouter()

# Mock database for now - replace with actual database operations
mock_booking_links = []
mock_booking_templates = []
mock_bookings = []
mock_analytics_events = []

def get_client_key(request: Request) -> str:
    """Extract client identifier for rate limiting"""
    # In production, this might be user ID, IP address, or API key
    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"

@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "bookings"}

@router.get("/public/{token}")
async def get_public_link(token: str, request: Request):
    """Get public link metadata including template questions"""
    # Rate limiting for public endpoints
    client_key = get_client_key(request)
    if not check_rate_limit(client_key, max_requests=200, window_seconds=3600):
        audit_logger.log_rate_limit_exceeded(
            client_key=client_key,
            endpoint="/public/{token}",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Validate token format
    if not SecurityUtils.validate_token_format(token):
        audit_logger.log_suspicious_activity(
            activity_type="invalid_token_format",
            details={"token": token, "endpoint": "/public/{token}"},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        raise HTTPException(status_code=404, detail="Invalid token format")
    
    # TODO: Replace with actual database lookup
    # Mock response for now
    mock_template_questions = [
        {"id": "name", "label": "Your Name", "required": True, "type": "text"},
        {"id": "email", "label": "Email Address", "required": True, "type": "email"},
        {"id": "company", "label": "Company", "required": False, "type": "text"},
        {"id": "message", "label": "Message", "required": False, "type": "textarea"},
    ]
    
    return {
        "data": {
            "title": "Sample Booking Link",
            "description": "Book a meeting with us",
            "template_questions": mock_template_questions,
            "duration_options": [15, 30, 60, 120],
            "is_active": True,
        }
    }

@router.get("/public/{token}/availability")
async def get_public_availability(token: str, duration: int = 30, request: Request = None):
    """Get available time slots for a public link"""
    # Rate limiting for public endpoints
    client_key = get_client_key(request) if request else "unknown"
    if not check_rate_limit(client_key, max_requests=100, window_seconds=3600):
        if request:
            audit_logger.log_rate_limit_exceeded(
                client_key=client_key,
                endpoint="/public/{token}/availability",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent")
            )
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Validate token format
    if not SecurityUtils.validate_token_format(token):
        if request:
            audit_logger.log_suspicious_activity(
                activity_type="invalid_token_format",
                details={"token": token, "endpoint": "/public/{token}/availability"},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent")
            )
        raise HTTPException(status_code=404, detail="Invalid token format")
    
    # TODO: Replace with actual availability calculation
    # Mock availability data
    base_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    slots = []
    
    for i in range(5):  # Next 5 days
        for hour in range(9, 17):  # 9 AM to 5 PM
            start_time = base_date + timedelta(days=i, hours=hour)
            end_time = start_time + timedelta(minutes=duration)
            
            slots.append({
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "available": True,
            })
    
    return {
        "data": {
            "slots": slots,
            "duration": duration,
            "timezone": "UTC",
        }
    }

@router.post("/public/{token}/book")
async def create_public_booking(token: str, booking_data: dict, request: Request):
    """Create a booking from a public link"""
    # Rate limiting for public endpoints
    client_key = get_client_key(request)
    if not check_rate_limit(client_key, max_requests=10, window_seconds=3600):
        audit_logger.log_rate_limit_exceeded(
            client_key=client_key,
            endpoint="/public/{token}/book",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Validate token format
    if not SecurityUtils.validate_token_format(token):
        audit_logger.log_suspicious_activity(
            activity_type="invalid_token_format",
            details={"token": token, "endpoint": "/public/{token}/book"},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        raise HTTPException(status_code=404, detail="Invalid token format")
    
    # Validate required fields
    required_fields = ["start", "end", "attendeeEmail"]
    for field in required_fields:
        if field not in booking_data:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    
    # Sanitize input
    attendee_email = SecurityUtils.sanitize_input(booking_data["attendeeEmail"])
    answers = {k: SecurityUtils.sanitize_input(str(v)) for k, v in booking_data.get("answers", {}).items()}
    
    # Mock booking creation
    booking_id = str(uuid.uuid4())
    mock_booking = {
        "id": booking_id,
        "token": token,
        "start_at": booking_data["start"],
        "end_at": booking_data["end"],
        "attendee_email": attendee_email,
        "answers": answers,
        "created_at": datetime.now().isoformat(),
    }
    
    mock_bookings.append(mock_booking)
    
    # Audit logging
    audit_logger.log_booking_creation(
        link_id=token,
        booking_id=booking_id,
        attendee_email=attendee_email,
        start_time=booking_data["start"],
        end_time=booking_data["end"],
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    # TODO: Create calendar event
    # calendar_event_id = await create_booking_calendar_event(mock_booking)
    
    # TODO: Send confirmation emails
    # await send_confirmation_email(mock_booking)
    
    # TODO: Track analytics
    # await track_analytics_event(token, "booked")
    
    return {
        "data": {
            "id": booking_id,
            "message": "Booking created successfully",
            "calendar_event_id": None,  # TODO: Replace with actual event ID
        }
    }

# Owner API endpoints
@router.post("/links")
async def create_booking_link(link_data: dict, request: Request):
    """Create a new evergreen booking link"""
    # Rate limiting for authenticated endpoints
    client_key = get_client_key(request)
    if not check_rate_limit(client_key, max_requests=50, window_seconds=3600):
        audit_logger.log_rate_limit_exceeded(
            client_key=client_key,
            endpoint="/links",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Sanitize input
    title = SecurityUtils.sanitize_input(link_data.get("title", ""))
    description = SecurityUtils.sanitize_input(link_data.get("description", ""))
    
    # TODO: Replace with actual database creation
    link_id = str(uuid.uuid4())
    slug = link_data.get("slug") or TokenGenerator.generate_slug()
    
    new_link = {
        "id": link_id,
        "owner_user_id": "mock_user_id",  # TODO: Get from auth
        "slug": slug,
        "title": title,
        "description": description,
        "is_active": True,
        "settings": {
            "duration": link_data.get("duration", 30),
            "buffer_before": link_data.get("buffer_before", 0),
            "buffer_after": link_data.get("buffer_after", 0),
            "max_per_day": link_data.get("max_per_day", 3),
            "max_per_week": link_data.get("max_per_week", 10),
            "advance_days": link_data.get("advance_days", 1),
            "max_advance_days": link_data.get("max_advance_days", 30),
        },
        "template_id": None,  # TODO: Create template if provided
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    
    mock_booking_links.append(new_link)
    
    # Audit logging
    audit_logger.log_link_creation(
        user_id="mock_user_id",  # TODO: Get from auth
        link_id=link_id,
        link_title=title,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    return {
        "data": {
            "id": link_id,
            "slug": slug,
            "public_url": f"/public/bookings/{slug}",
            "message": "Booking link created successfully",
        }
    }

@router.get("/links")
async def list_booking_links(request: Request = None):
    """List all booking links for the authenticated user"""
    # Rate limiting for authenticated endpoints
    if request:
        client_key = get_client_key(request)
        if not check_rate_limit(client_key, max_requests=100, window_seconds=3600):
            audit_logger.log_rate_limit_exceeded(
                client_key=client_key,
                endpoint="/links",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent")
            )
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # TODO: Replace with actual database query
    return {
        "data": mock_booking_links,
        "total": len(mock_booking_links),
    }

@router.get("/links/{link_id}")
async def get_booking_link(link_id: str, request: Request = None):
    """Get a specific booking link"""
    # Rate limiting for authenticated endpoints
    if request:
        client_key = get_client_key(request)
        if not check_rate_limit(client_key, max_requests=100, window_seconds=3600):
            audit_logger.log_rate_limit_exceeded(
                client_key=client_key,
                endpoint=f"/links/{link_id}",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent")
            )
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # TODO: Replace with actual database lookup
    link = next((l for l in mock_booking_links if l["id"] == link_id), None)
    if not link:
        raise HTTPException(status_code=404, detail="Booking link not found")
    
    return {"data": link}

@router.patch("/links/{link_id}")
async def update_booking_link(link_id: str, updates: dict, request: Request):
    """Update a booking link's settings"""
    # Rate limiting for authenticated endpoints
    client_key = get_client_key(request)
    if not check_rate_limit(client_key, max_requests=50, window_seconds=3600):
        audit_logger.log_rate_limit_exceeded(
            client_key=client_key,
            endpoint=f"/links/{link_id}",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # TODO: Replace with actual database update
    link = next((l for l in mock_booking_links if l["id"] == link_id), None)
    if not link:
        raise HTTPException(status_code=404, detail="Booking link not found")
    
    # Sanitize updates
    sanitized_updates = {}
    for key, value in updates.items():
        if key in ["title", "description"]:
            sanitized_updates[key] = SecurityUtils.sanitize_input(str(value))
        else:
            sanitized_updates[key] = value
    
    # Update fields
    changes = {}
    for key, value in sanitized_updates.items():
        if key in link:
            old_value = link[key]
            link[key] = value
            changes[key] = {"old": old_value, "new": value}
        elif key in link.get("settings", {}):
            old_value = link["settings"][key]
            link["settings"][key] = value
            changes[f"settings.{key}"] = {"old": old_value, "new": value}
    
    link["updated_at"] = datetime.now().isoformat()
    
    # Audit logging
    if changes:
        audit_logger.log_link_update(
            user_id="mock_user_id",  # TODO: Get from auth
            link_id=link_id,
            changes=changes,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
    
    return {"data": link, "message": "Booking link updated successfully"}

@router.post("/links/{link_id}:duplicate")
async def duplicate_booking_link(link_id: str, request: Request):
    """Duplicate an existing booking link"""
    # Rate limiting for authenticated endpoints
    client_key = get_client_key(request)
    if not check_rate_limit(client_key, max_requests=20, window_seconds=3600):
        audit_logger.log_rate_limit_exceeded(
            client_key=client_key,
            endpoint=f"/links/{link_id}:duplicate",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # TODO: Replace with actual database duplication
    original = next((l for l in mock_booking_links if l["id"] == link_id), None)
    if not original:
        raise HTTPException(status_code=404, detail="Booking link not found")
    
    new_id = str(uuid.uuid4())
    new_slug = f"{original['slug']}_copy_{TokenGenerator.generate_slug()[:4]}"
    
    duplicated = {
        **original,
        "id": new_id,
        "slug": new_slug,
        "title": f"{original['title']} (Copy)",
        "is_active": False,  # Start as inactive
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    
    mock_booking_links.append(duplicated)
    
    # Audit logging
    audit_logger.log_event(
        event_type=AuditEventType.LINK_DUPLICATED,
        user_id="mock_user_id",  # TODO: Get from auth
        resource_id=link_id,
        details={"new_link_id": new_id, "new_slug": new_slug},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    return {
        "data": {
            "id": new_id,
            "slug": new_slug,
            "message": "Booking link duplicated successfully",
        }
    }

@router.post("/links/{link_id}:toggle")
async def toggle_booking_link(link_id: str, request: Request):
    """Toggle a booking link's active status"""
    # Rate limiting for authenticated endpoints
    client_key = get_client_key(request)
    if not check_rate_limit(client_key, max_requests=50, window_seconds=3600):
        audit_logger.log_rate_limit_exceeded(
            client_key=client_key,
            endpoint=f"/links/{link_id}:toggle",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # TODO: Replace with actual database toggle
    link = next((l for l in mock_booking_links if l["id"] == link_id), None)
    if not link:
        raise HTTPException(status_code=404, detail="Booking link not found")
    
    old_status = link["is_active"]
    link["is_active"] = not link["is_active"]
    link["updated_at"] = datetime.now().isoformat()
    
    # Audit logging
    audit_logger.log_link_toggle(
        user_id="mock_user_id",  # TODO: Get from auth
        link_id=link_id,
        new_status=link["is_active"],
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    return {
        "data": {
            "id": link_id,
            "is_active": link["is_active"],
            "message": f"Booking link {'activated' if link['is_active'] else 'deactivated'} successfully",
        }
    }

@router.post("/links/{link_id}/one-time")
async def create_one_time_link(link_id: str, one_time_data: dict, request: Request):
    """Create a one-time link for a specific recipient"""
    # Rate limiting for authenticated endpoints
    client_key = get_client_key(request)
    if not check_rate_limit(client_key, max_requests=20, window_seconds=3600):
        audit_logger.log_rate_limit_exceeded(
            client_key=client_key,
            endpoint=f"/links/{link_id}/one-time",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # TODO: Replace with actual database creation
    link = next((l for l in mock_booking_links if l["id"] == link_id), None)
    if not link:
        raise HTTPException(status_code=404, detail="Booking link not found")
    
    token = TokenGenerator.generate_one_time_token()
    expires_at = datetime.now() + timedelta(days=one_time_data.get("expires_in_days", 7))
    
    # Sanitize recipient data
    recipient_email = SecurityUtils.sanitize_input(one_time_data.get("recipient_email", ""))
    recipient_name = SecurityUtils.sanitize_input(one_time_data.get("recipient_name", ""))
    
    one_time_link = {
        "id": str(uuid.uuid4()),
        "booking_link_id": link_id,
        "recipient_email": recipient_email,
        "recipient_name": recipient_name,
        "token": token,
        "expires_at": expires_at.isoformat(),
        "status": "active",
        "created_at": datetime.now().isoformat(),
    }
    
    # TODO: Store in database
    
    # Audit logging
    audit_logger.log_event(
        event_type=AuditEventType.ONE_TIME_LINK_CREATED,
        user_id="mock_user_id",  # TODO: Get from auth
        resource_id=link_id,
        details={
            "one_time_link_id": one_time_link["id"],
            "recipient_email_hash": SecurityUtils.hash_email(recipient_email),
            "expires_at": expires_at.isoformat()
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    return {
        "data": {
            "token": token,
            "public_url": f"/public/bookings/{token}",
            "expires_at": expires_at.isoformat(),
            "message": "One-time link created successfully",
        }
    }

@router.get("/links/{link_id}/analytics")
async def get_link_analytics(link_id: str, request: Request = None):
    """Get analytics for a specific booking link"""
    # Rate limiting for authenticated endpoints
    if request:
        client_key = get_client_key(request)
        if not check_rate_limit(client_key, max_requests=100, window_seconds=3600):
            audit_logger.log_rate_limit_exceeded(
                client_key=client_key,
                endpoint=f"/links/{link_id}/analytics",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent")
            )
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # TODO: Replace with actual analytics calculation
    link = next((l for l in mock_booking_links if l["id"] == link_id), None)
    if not link:
        raise HTTPException(status_code=404, detail="Booking link not found")
    
    # Mock analytics data
    mock_analytics = {
        "link_id": link_id,
        "views": 142,
        "bookings": 12,
        "conversion_rate": "8.5%",
        "last_viewed": datetime.now().isoformat(),
        "top_referrers": ["Direct", "Email", "LinkedIn"],
        "recent_activity": [
            {"type": "view", "timestamp": datetime.now().isoformat()},
            {"type": "booking", "timestamp": (datetime.now() - timedelta(hours=2)).isoformat()},
        ],
    }
    
    # Audit logging
    if request:
        audit_logger.log_event(
            event_type=AuditEventType.ANALYTICS_VIEWED,
            user_id="mock_user_id",  # TODO: Get from auth
            resource_id=link_id,
            details={"analytics_type": "link_performance"},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
    
    return {"data": mock_analytics}


