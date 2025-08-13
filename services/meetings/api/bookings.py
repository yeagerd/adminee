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
from services.meetings.models import get_session
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
    
    # Database lookup for the link
    with get_session() as session:
        # Check if it's a one-time link
        one_time_link = session.query(OneTimeLink).filter_by(token=token).first()
        if one_time_link:
            # Check if expired or used
            if one_time_link.expires_at and one_time_link.expires_at < datetime.now():
                raise HTTPException(status_code=404, detail="Link has expired")
            if one_time_link.status != "active":
                raise HTTPException(status_code=404, detail="Link has already been used")
            
            # Get the parent booking link
            booking_link = session.query(BookingLink).filter_by(id=one_time_link.booking_link_id).first()
            if not booking_link or not booking_link.is_active:
                raise HTTPException(status_code=404, detail="Booking link not found or inactive")
        else:
            # Check if it's an evergreen link
            booking_link = session.query(BookingLink).filter_by(slug=token).first()
            if not booking_link or not booking_link.is_active:
                raise HTTPException(status_code=404, detail="Booking link not found or inactive")
        
        # Get template questions if available
        template_questions = []
        if booking_link.template_id is not None:
            template = session.query(BookingTemplate).filter_by(id=booking_link.template_id).first()
            if template is not None and template.questions is not None:
                template_questions = template.questions
        
        # Default questions if no template
        if not template_questions:
            template_questions = [
                {"id": "name", "label": "Your Name", "required": True, "type": "text"},
                {"id": "email", "label": "Email Address", "required": True, "type": "email"},
                {"id": "company", "label": "Company", "required": False, "type": "text"},
                {"id": "message", "label": "Message", "required": False, "type": "textarea"},
            ]
        
        # Get duration from settings
        duration_options = [15, 30, 60, 120]
        if booking_link.settings and "duration" in booking_link.settings:
            duration_options = [booking_link.settings["duration"]] + [d for d in duration_options if d != booking_link.settings["duration"]]
        
        return {
            "data": {
                "title": booking_link.slug,  # Use slug as title for now
                "description": "Book a meeting with us",
                "template_questions": template_questions,
                "duration_options": duration_options,
                "is_active": booking_link.is_active,
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
    
    # Database lookup for the link
    with get_session() as session:
        # Check if it's a one-time link
        one_time_link = session.query(OneTimeLink).filter_by(token=token).first()
        if one_time_link is not None:
            if one_time_link.expires_at is not None and one_time_link.expires_at < datetime.now():
                raise HTTPException(status_code=404, detail="Link has expired")
            if one_time_link.status != "active":
                raise HTTPException(status_code=404, detail="Link has already been used")
            
            booking_link = session.query(BookingLink).filter_by(id=one_time_link.booking_link_id).first()
        else:
            booking_link = session.query(BookingLink).filter_by(slug=token).first()
        
        if not booking_link or not booking_link.is_active:
            raise HTTPException(status_code=404, detail="Booking link not found or inactive")
        
        # TODO: Replace with actual availability calculation using Office Service
        # For now, generate mock availability based on business hours
        base_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        slots = []
        
        # Apply business hours from settings
        business_hours = booking_link.settings.get("business_hours", {}) if booking_link.settings else {}
        
        for i in range(5):  # Next 5 days
            for hour in range(9, 17):  # 9 AM to 5 PM
                start_time = base_date + timedelta(days=i, hours=hour)
                end_time = start_time + timedelta(minutes=duration)
                
                # Check if this time falls within business hours
                day_name = start_time.strftime("%A").lower()
                if day_name in business_hours and business_hours[day_name].get("enabled", True):
                    start_hour = business_hours[day_name].get("start", "09:00")
                    end_hour = business_hours[day_name].get("end", "17:00")
                    
                    start_hour_int = int(start_hour.split(":")[0])
                    end_hour_int = int(end_hour.split(":")[0])
                    
                    if start_hour_int <= hour < end_hour_int:
                        slots.append({
                            "start": start_time.isoformat(),
                            "end": end_time.isoformat(),
                            "available": True,
                        })
                else:
                    # Default business hours
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
    
    # Database operations
    with get_session() as session:
        # Find the link
        one_time_link = session.query(OneTimeLink).filter_by(token=token).first()
        if one_time_link:
            if one_time_link.expires_at and one_time_link.expires_at < datetime.now():
                raise HTTPException(status_code=404, detail="Link has expired")
            if one_time_link.status != "active":
                raise HTTPException(status_code=404, detail="Link has already been used")
            
            booking_link = session.query(BookingLink).filter_by(id=one_time_link.booking_link_id).first()
            link_id = one_time_link.booking_link_id
            one_time_link_id = one_time_link.id
            
            # Mark one-time link as used
            one_time_link.status = "used"
            session.commit()
        else:
            booking_link = session.query(BookingLink).filter_by(slug=token).first()
            if not booking_link or not booking_link.is_active:
                raise HTTPException(status_code=404, detail="Booking link not found or inactive")
            
            link_id = booking_link.id
            one_time_link_id = None
        
        # Create the booking
        booking = Booking(
            link_id=link_id,
            one_time_link_id=one_time_link_id,
            start_at=datetime.fromisoformat(booking_data["start"]),
            end_at=datetime.fromisoformat(booking_data["end"]),
            attendee_email=attendee_email,
            answers=answers,
        )
        
        session.add(booking)
        session.commit()
        session.refresh(booking)
        
        # Track analytics event
        analytics_event = AnalyticsEvent(
            link_id=link_id,
            event_type="booked",
            referrer=request.headers.get("referer", "direct")
        )
        session.add(analytics_event)
        session.commit()
        
        # TODO: Create calendar event
        # calendar_event_id = await create_booking_calendar_event(booking)
        
        # TODO: Send confirmation emails
        # await send_confirmation_email(booking)
        
        # Audit logging
        audit_logger.log_booking_creation(
            link_id=token,
            booking_id=str(booking.id),
            attendee_email=attendee_email,
            start_time=booking_data["start"],
            end_time=booking_data["end"],
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        return {
            "data": {
                "id": str(booking.id),
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
    
    # TODO: Get actual user ID from authentication
    owner_user_id = "mock_user_id"  # TODO: Get from auth
    
    # Database creation
    with get_session() as session:
        # Generate unique slug
        slug = link_data.get("slug") or TokenGenerator.generate_slug()
        
        # Check if slug already exists
        existing_link = session.query(BookingLink).filter_by(slug=slug).first()
        if existing_link:
            # Generate a new unique slug
            counter = 1
            while existing_link:
                new_slug = f"{slug}_{counter}"
                existing_link = session.query(BookingLink).filter_by(slug=new_slug).first()
                counter += 1
            slug = new_slug
        
        # Create template if provided
        template_id = None
        if link_data.get("template_name"):
            template = BookingTemplate(
                owner_user_id=owner_user_id,
                name=link_data["template_name"],
                questions=link_data.get("questions", []),
                email_followup_enabled=link_data.get("emailFollowup", False)
            )
            session.add(template)
            session.commit()
            session.refresh(template)
            template_id = template.id
        
        # Create the booking link
        new_link = BookingLink(
            owner_user_id=owner_user_id,
            slug=slug,
            is_active=True,
            settings={
                "duration": link_data.get("duration", 30),
                "buffer_before": link_data.get("buffer_before", 0),
                "buffer_after": link_data.get("buffer_after", 0),
                "max_per_day": link_data.get("max_per_day", 3),
                "max_per_week": link_data.get("max_per_week", 10),
                "advance_days": link_data.get("advance_days", 1),
                "max_advance_days": link_data.get("max_advance_days", 30),
                "business_hours": link_data.get("business_hours", {}),
                "holiday_exclusions": link_data.get("holiday_exclusions", []),
                "last_minute_cutoff": link_data.get("last_minute_cutoff", 2),
            },
            template_id=template_id,
        )
        
        session.add(new_link)
        session.commit()
        session.refresh(new_link)
        
        # Audit logging
        audit_logger.log_link_creation(
            user_id=owner_user_id,  # TODO: Get from auth
            link_id=str(new_link.id),
            link_title=title,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        return {
            "data": {
                "id": str(new_link.id),
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
    
    # TODO: Get actual user ID from authentication
    owner_user_id = "mock_user_id"  # TODO: Get from auth
    
    # Database query
    with get_session() as session:
        links = session.query(BookingLink).filter_by(owner_user_id=owner_user_id).all()
        
        # Convert to dict format for response
        links_data = []
        for link in links:
            # Get analytics for conversion rate
            total_views = session.query(AnalyticsEvent).filter_by(
                link_id=link.id, 
                event_type="view"
            ).count()
            
            total_bookings = session.query(AnalyticsEvent).filter_by(
                link_id=link.id, 
                event_type="booked"
            ).count()
            
            conversion_rate = "0%"
            if total_views > 0:
                conversion_rate = f"{(total_bookings / total_views * 100):.1f}%"
            
            links_data.append({
                "id": str(link.id),
                "owner_user_id": link.owner_user_id,
                "slug": link.slug,
                "is_active": link.is_active,
                "settings": link.settings,
                "template_id": str(link.template_id) if link.template_id else None,
                "created_at": link.created_at.isoformat() if link.created_at else None,
                "updated_at": link.updated_at.isoformat() if link.updated_at else None,
                "total_views": total_views,
                "total_bookings": total_bookings,
                "conversion_rate": conversion_rate,
            })
        
        return {
            "data": links_data,
            "total": len(links_data),
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
    
    # TODO: Get actual user ID from authentication
    owner_user_id = "mock_user_id"  # TODO: Get from auth
    
    # Database lookup
    with get_session() as session:
        link = session.query(BookingLink).filter_by(id=link_id, owner_user_id=owner_user_id).first()
        if not link:
            raise HTTPException(status_code=404, detail="Booking link not found")
        
        return {"data": {
            "id": str(link.id),
            "owner_user_id": link.owner_user_id,
            "slug": link.slug,
            "is_active": link.is_active,
            "settings": link.settings,
            "template_id": str(link.template_id) if link.template_id else None,
            "created_at": link.created_at.isoformat() if link.created_at else None,
            "updated_at": link.updated_at.isoformat() if link.updated_at else None,
        }}

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
    
    # TODO: Get actual user ID from authentication
    owner_user_id = "mock_user_id"  # TODO: Get from auth
    
    # Database update
    with get_session() as session:
        link = session.query(BookingLink).filter_by(id=link_id, owner_user_id=owner_user_id).first()
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
            if key in ["title", "description"]:
                # These would need to be added to the model if we want to store them
                continue
            elif key == "settings" and isinstance(value, dict):
                # Merge settings
                old_settings = link.settings or {}
                new_settings = {**old_settings, **value}
                if new_settings != old_settings:
                    changes[f"settings"] = {"old": old_settings, "new": new_settings}
                    link.settings = new_settings
            elif key == "is_active":
                old_value = link.is_active
                link.is_active = value
                changes[key] = {"old": old_value, "new": value}
        
        link.updated_at = datetime.now()
        session.commit()
        
        # Audit logging
        if changes:
            audit_logger.log_link_update(
                user_id=owner_user_id,  # TODO: Get from auth
                link_id=link_id,
                changes=changes,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent")
            )
        
        return {"data": {
            "id": str(link.id),
            "owner_user_id": link.owner_user_id,
            "slug": link.slug,
            "is_active": link.is_active,
            "settings": link.settings,
            "template_id": str(link.template_id) if link.template_id else None,
            "created_at": link.created_at.isoformat() if link.created_at else None,
            "updated_at": link.updated_at.isoformat() if link.updated_at else None,
        }, "message": "Booking link updated successfully"}

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
    
    # TODO: Get actual user ID from authentication
    owner_user_id = "mock_user_id"  # TODO: Get from auth
    
    # Database duplication
    with get_session() as session:
        original = session.query(BookingLink).filter_by(id=link_id, owner_user_id=owner_user_id).first()
        if not original:
            raise HTTPException(status_code=404, detail="Booking link not found")
        
        # Generate unique slug
        new_slug = f"{original.slug}_copy_{TokenGenerator.generate_slug()[:4]}"
        existing_link = session.query(BookingLink).filter_by(slug=new_slug).first()
        counter = 1
        while existing_link:
            new_slug = f"{original.slug}_copy_{TokenGenerator.generate_slug()[:4]}_{counter}"
            existing_link = session.query(BookingLink).filter_by(slug=new_slug).first()
            counter += 1
        
        # Create duplicated link
        duplicated = BookingLink(
            owner_user_id=owner_user_id,
            slug=new_slug,
            is_active=False,  # Start as inactive
            settings=original.settings,
            template_id=original.template_id,
        )
        
        session.add(duplicated)
        session.commit()
        session.refresh(duplicated)
        
        # Audit logging
        audit_logger.log_event(
            event_type=AuditEventType.LINK_DUPLICATED,
            user_id=owner_user_id,  # TODO: Get from auth
            resource_id=link_id,
            details={"new_link_id": str(duplicated.id), "new_slug": new_slug},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        return {
            "data": {
                "id": str(duplicated.id),
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
    
    # TODO: Get actual user ID from authentication
    owner_user_id = "mock_user_id"  # TODO: Get from auth
    
    # Database toggle
    with get_session() as session:
        link = session.query(BookingLink).filter_by(id=link_id, owner_user_id=owner_user_id).first()
        if not link:
            raise HTTPException(status_code=404, detail="Booking link not found")
        
        old_status = link.is_active
        link.is_active = not link.is_active
        link.updated_at = datetime.now()
        session.commit()
        
        # Audit logging
        audit_logger.log_link_toggle(
            user_id=owner_user_id,  # TODO: Get from auth
            link_id=link_id,
            new_status=link.is_active,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        return {
            "data": {
                "id": link_id,
                "is_active": link.is_active,
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
    
    # TODO: Get actual user ID from authentication
    owner_user_id = "mock_user_id"  # TODO: Get from auth
    
    # Database creation
    with get_session() as session:
        link = session.query(BookingLink).filter_by(id=link_id, owner_user_id=owner_user_id).first()
        if not link:
            raise HTTPException(status_code=404, detail="Booking link not found")
        
        token = TokenGenerator.generate_one_time_token()
        expires_at = datetime.now() + timedelta(days=one_time_data.get("expires_in_days", 7))
        
        # Sanitize recipient data
        recipient_email = SecurityUtils.sanitize_input(one_time_data.get("recipient_email", ""))
        recipient_name = SecurityUtils.sanitize_input(one_time_data.get("recipient_name", ""))
        
        # Create one-time link
        one_time_link = OneTimeLink(
            booking_link_id=link_id,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            token=token,
            expires_at=expires_at,
            status="active",
        )
        
        session.add(one_time_link)
        session.commit()
        session.refresh(one_time_link)
        
        # Audit logging
        audit_logger.log_event(
            event_type=AuditEventType.ONE_TIME_LINK_CREATED,
            user_id=owner_user_id,  # TODO: Get from auth
            resource_id=link_id,
            details={
                "one_time_link_id": str(one_time_link.id),
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
    
    # TODO: Get actual user ID from authentication
    owner_user_id = "mock_user_id"  # TODO: Get from auth
    
    # Database analytics calculation
    with get_session() as session:
        link = session.query(BookingLink).filter_by(id=link_id, owner_user_id=owner_user_id).first()
        if not link:
            raise HTTPException(status_code=404, detail="Booking link not found")
        
        # Get analytics data
        views = session.query(AnalyticsEvent).filter_by(
            link_id=link_id, 
            event_type="view"
        ).count()
        
        bookings = session.query(AnalyticsEvent).filter_by(
            link_id=link_id, 
            event_type="booked"
        ).count()
        
        conversion_rate = "0%"
        if views > 0:
            conversion_rate = f"{(bookings / views * 100):.1f}%"
        
        # Get recent activity
        recent_activity = session.query(AnalyticsEvent).filter_by(
            link_id=link_id
        ).order_by(AnalyticsEvent.occurred_at.desc()).limit(10).all()
        
        activity_data = []
        for event in recent_activity:
            activity_data.append({
                "type": event.event_type,
                "timestamp": event.occurred_at.isoformat() if event.occurred_at else None
            })
        
        # Mock referrer data for now
        top_referrers = ["Direct", "Email", "LinkedIn"]
        
        analytics_data = {
            "link_id": link_id,
            "views": views,
            "bookings": bookings,
            "conversion_rate": conversion_rate,
            "last_viewed": recent_activity[0].occurred_at.isoformat() if recent_activity else None,
            "top_referrers": top_referrers,
            "recent_activity": activity_data,
        }
        
        # Audit logging
        if request:
            audit_logger.log_event(
                event_type=AuditEventType.ANALYTICS_VIEWED,
                user_id=owner_user_id,  # TODO: Get from auth
                resource_id=link_id,
                details={"analytics_type": "link_performance"},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent")
            )
        
        return {"data": analytics_data}


