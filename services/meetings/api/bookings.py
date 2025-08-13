import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional



from fastapi import APIRouter, Depends, Request

from services.common.http_errors import (
    AuthError,
    BrieflyAPIError,
    NotFoundError,
    RateLimitError,
    ServiceError,
    ValidationError,
)
from services.meetings.api.auth import get_user_id_from_request, verify_api_key_auth
from services.meetings.models import get_session
from services.meetings.models.bookings import (
    AnalyticsEvent,
    Booking,
    BookingLink,
    BookingTemplate,
    OneTimeLink,
)
from services.meetings.schemas.bookings import (
    AnalyticsResponse,
    AvailabilityResponse,
    BookingLinkFilters,
    BookingLinkResponse,
    BookingLinksListResponse,
    BookingResponse,
    CreateBookingLinkRequest,
    CreateOneTimeLinkRequest,
    CreatePublicBookingRequest,
    CreateTemplateRequest,
    OneTimeLinkResponse,
    OneTimeLinksListResponse,
    PaginationParams,
    PublicLinkResponse,
    SuccessResponse,
    TemplateResponse,
    TemplatesListResponse,
    UpdateBookingLinkRequest,
    UpdateTemplateRequest,
)
from services.meetings.services.audit_logger import AuditEventType, audit_logger
from services.meetings.services.booking_emails import (
    send_confirmation_email,
    send_follow_up_email,
)
from services.meetings.services.booking_events import create_booking_calendar_event
from services.meetings.services.contacts_integration import (
    create_contact,
    search_contacts,
)
from services.meetings.services.security import (
    SecurityUtils,
    TokenGenerator,
    check_rate_limit,
    get_remaining_requests,
)

router = APIRouter()


def get_client_key(request: Request) -> str:
    """Extract client identifier for rate limiting"""
    # In production, this might be user ID, IP address, or API key
    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"


@router.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy", "service": "bookings"}


@router.get("/public/{token}", response_model=PublicLinkResponse)
async def get_public_link(token: str, request: Request) -> PublicLinkResponse:
    """Get public link metadata including template questions"""
    # Rate limiting for public endpoints
    client_key = get_client_key(request)
    if not check_rate_limit(client_key, max_requests=200, window_seconds=3600):
        audit_logger.log_rate_limit_exceeded(
            client_key=client_key,
            endpoint="/public/{token}",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        raise RateLimitError(message="Rate limit exceeded")

    # Validate token format
    if not SecurityUtils.validate_token_format(token):
        audit_logger.log_suspicious_activity(
            activity_type="invalid_token_format",
            details={"token": token, "endpoint": "/public/{token}"},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        raise ValidationError(message="Invalid token format")

    # Database lookup for the link
    with get_session() as session:
        # Check if it's a one-time link
        one_time_link = session.query(OneTimeLink).filter_by(token=token).first()
        if one_time_link is not None:
            # Check if expired or used
            if (
                one_time_link.expires_at is not None  # type: ignore
                and one_time_link.expires_at < datetime.now()  # type: ignore
            ):
                raise NotFoundError("Link", "expired")
            if one_time_link.status != "active":  # type: ignore
                raise NotFoundError("Link", "already used")

            # Get the parent booking link
            booking_link = (
                session.query(BookingLink)
                .filter_by(id=one_time_link.booking_link_id)
                .first()
            )
            if not booking_link or not booking_link.is_active:
                raise NotFoundError("Booking link", "not found or inactive")
        else:
            # Check if it's an evergreen link
            booking_link = session.query(BookingLink).filter_by(slug=token).first()
            if not booking_link or not booking_link.is_active:
                raise NotFoundError("Booking link", "not found or inactive")

        # Get template questions if available
        template_questions: List[Dict[str, Any]] = []
        if booking_link.template_id is not None:
            template = (
                session.query(BookingTemplate)
                .filter_by(id=booking_link.template_id)
                .first()
            )
            if template is not None and template.questions is not None:
                template_questions = template.questions  # type: ignore[assignment]

        # Default questions if no template
        if not template_questions:
            template_questions = [
                {"id": "name", "label": "Your Name", "required": True, "type": "text"},
                {
                    "id": "email",
                    "label": "Email Address",
                    "required": True,
                    "type": "email",
                },
                {
                    "id": "company",
                    "label": "Company",
                    "required": False,
                    "type": "text",
                },
                {
                    "id": "message",
                    "label": "Message",
                    "required": False,
                    "type": "textarea",
                },
            ]

        # Get duration from settings
        duration_options = [15, 30, 60, 120]
        if booking_link.settings is not None and "duration" in booking_link.settings:
            duration_options = [booking_link.settings["duration"]] + [
                d for d in duration_options if d != booking_link.settings["duration"]
            ]

        # Track view analytics event
        analytics_event = AnalyticsEvent(
            link_id=booking_link.id,
            event_type="view",
            referrer=request.headers.get("referer", "direct"),
        )
        session.add(analytics_event)
        session.commit()

        return {
            "data": {
                "title": booking_link.slug,  # Use slug as title for now
                "description": "Book a meeting with us",
                "template_questions": template_questions,
                "duration_options": duration_options,
                "is_active": booking_link.is_active,
            }
        }


@router.get("/public/{token}/availability", response_model=AvailabilityResponse)
async def get_public_availability(
    token: str, duration: int = 30, request: Request = None
) -> AvailabilityResponse:
    """Get available time slots for a public link"""
    # Rate limiting for public endpoints
    client_key = get_client_key(request) if request else "unknown"
    if not check_rate_limit(client_key, max_requests=100, window_seconds=3600):
        if request:
            audit_logger.log_rate_limit_exceeded(
                client_key=client_key,
                endpoint="/public/{token}/availability",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
        raise RateLimitError(message="Rate limit exceeded")

    # Validate token format
    if not SecurityUtils.validate_token_format(token):
        if request:
            audit_logger.log_suspicious_activity(
                activity_type="invalid_token_format",
                details={"token": token, "endpoint": "/public/{token}/availability"},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
        raise ValidationError(message="Invalid token format")

    # Database lookup for the link
    with get_session() as session:
        # Check if it's a one-time link
        one_time_link = session.query(OneTimeLink).filter_by(token=token).first()
        if one_time_link is not None:
            if (
                one_time_link.expires_at is not None
                and one_time_link.expires_at < datetime.now()
            ):
                raise NotFoundError("Link", "expired")
            if one_time_link.status != "active":
                raise NotFoundError("Link", "already used")

            booking_link = (
                session.query(BookingLink)
                .filter_by(id=one_time_link.booking_link_id)
                .first()
            )
        else:
            booking_link = session.query(BookingLink).filter_by(slug=token).first()

        if not booking_link or not booking_link.is_active:
            raise NotFoundError("Booking link", "not found or inactive")

        # Use the enhanced availability calculation service
        from services.meetings.services.booking_availability import (
            compute_available_slots,
        )

        # Get owner user ID for availability calculation
        owner_user_id = booking_link.owner_user_id

        # Calculate availability for next 30 days
        start_date = datetime.now()
        end_date = start_date + timedelta(days=30)

        # Get settings for filtering
        settings: Dict[str, Any] = booking_link.settings or {}  # type: ignore[assignment]
        buffer_before = settings.get("buffer_before", 0)
        buffer_after = settings.get("buffer_after", 0)

        # Compute available slots with all settings applied
        availability_result = await compute_available_slots(
            user_id=owner_user_id,
            start=start_date,
            end=end_date,
            duration_minutes=duration,
            buffer_before_minutes=buffer_before,
            buffer_after_minutes=buffer_after,
            settings=settings,
        )

        return {
            "data": {
                "slots": availability_result.get("slots", []),
                "duration": duration,
                "timezone": "UTC",
            }
        }


@router.post("/public/{token}/book", response_model=SuccessResponse)
async def create_public_booking(
    token: str, booking_data: CreatePublicBookingRequest, request: Request
) -> SuccessResponse:
    """Create a booking from a public link"""
    # Rate limiting for public endpoints
    client_key = get_client_key(request)
    if not check_rate_limit(client_key, max_requests=10, window_seconds=3600):
        audit_logger.log_rate_limit_exceeded(
            client_key=client_key,
            endpoint="/public/{token}/book",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        raise RateLimitError(message="Rate limit exceeded")

    # Validate token format
    if not SecurityUtils.validate_token_format(token):
        audit_logger.log_suspicious_activity(
            activity_type="invalid_token_format",
            details={"token": token, "endpoint": "/public/{token}/book"},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        raise ValidationError(message="Invalid token format")

    # Validate required fields
    required_fields = ["start", "end", "attendee_email"]
    for field in required_fields:
        if not hasattr(booking_data, field) or getattr(booking_data, field) is None:
            raise ValidationError(message=f"Missing required field: {field}")

    # Sanitize input
    attendee_email = SecurityUtils.sanitize_input(booking_data.attendee_email)
    answers = {
        k: SecurityUtils.sanitize_input(str(v)) for k, v in booking_data.answers.items()
    }

    # Database operations
    with get_session() as session:
        # Find the link
        one_time_link = session.query(OneTimeLink).filter_by(token=token).first()
        if one_time_link is not None:
            if (
                one_time_link.expires_at is not None
                and one_time_link.expires_at < datetime.now()
            ):
                raise NotFoundError("Link", "expired")
            if one_time_link.status != "active":
                raise NotFoundError("Link", "already used")

            booking_link = (
                session.query(BookingLink)
                .filter_by(id=one_time_link.booking_link_id)
                .first()
            )
            link_id = one_time_link.booking_link_id
            one_time_link_id = one_time_link.id

            # Mark one-time link as used
            one_time_link.status = "used"
            session.commit()
        else:
            booking_link = session.query(BookingLink).filter_by(slug=token).first()
            if not booking_link or not booking_link.is_active:
                raise NotFoundError("Booking link", "not found or inactive")

            link_id = booking_link.id
            one_time_link_id = None

        # Create the booking
        booking = Booking(
            link_id=link_id,
            one_time_link_id=one_time_link_id,
            start_at=booking_data.start,
            end_at=booking_data.end,
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
            referrer=request.headers.get("referer", "direct"),
        )
        session.add(analytics_event)
        session.commit()

        # Create calendar event
        calendar_event_id = await create_booking_calendar_event(booking)

        # Send confirmation emails
        await send_confirmation_email(booking)

        # Audit logging
        audit_logger.log_booking_creation(
            link_id=token,
            booking_id=str(booking.id),
            attendee_email=attendee_email,
            start_time=booking_data.start.isoformat(),
            end_time=booking_data.end.isoformat(),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        return SuccessResponse(
            data={
                "id": str(booking.id),
                "message": "Booking created successfully",
                "calendar_event_id": calendar_event_id,
            },
            message="Booking created successfully",
        )


# Owner API endpoints
@router.post("/links")
async def create_booking_link(
    link_data: dict, request: Request, service_name: str = Depends(verify_api_key_auth)
) -> Dict[str, Any]:
    """Create a new evergreen booking link"""
    # Rate limiting for authenticated endpoints
    client_key = get_client_key(request)
    if not check_rate_limit(client_key, max_requests=50, window_seconds=3600):
        audit_logger.log_rate_limit_exceeded(
            client_key=client_key,
            endpoint="/links",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        raise RateLimitError(message="Rate limit exceeded")

    # Get authenticated user ID
    owner_user_id = get_user_id_from_request(request)

    # Sanitize input
    title = SecurityUtils.sanitize_input(link_data.get("title", ""))
    description = SecurityUtils.sanitize_input(link_data.get("description", ""))

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
                existing_link = (
                    session.query(BookingLink).filter_by(slug=new_slug).first()
                )
                counter += 1
            slug = new_slug

        # Create template if provided
        template_id = None
        if link_data.get("template_name"):
            template = BookingTemplate(
                owner_user_id=owner_user_id,
                name=link_data["template_name"],
                questions=link_data.get("questions", []),
                email_followup_enabled=link_data.get("emailFollowup", False),
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
            user_id=owner_user_id,
            link_id=str(new_link.id),
            link_title=title,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
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
async def list_booking_links(
    request: Request = None, service_name: str = Depends(verify_api_key_auth)
) -> Dict[str, Any]:
    """List all booking links for the authenticated user"""
    # Rate limiting for authenticated endpoints
    if request:
        client_key = get_client_key(request)
        if not check_rate_limit(client_key, max_requests=100, window_seconds=3600):
            audit_logger.log_rate_limit_exceeded(
                client_key=client_key,
                endpoint="/links",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            raise RateLimitError(message="Rate limit exceeded")

    # Get authenticated user ID
    owner_user_id = get_user_id_from_request(request)

    # Database query
    with get_session() as session:
        links = session.query(BookingLink).filter_by(owner_user_id=owner_user_id).all()

        # Convert to dict format for response
        links_data = []
        for link in links:
            # Get analytics for conversion rate
            total_views = (
                session.query(AnalyticsEvent)
                .filter_by(link_id=link.id, event_type="view")
                .count()
            )

            total_bookings = (
                session.query(AnalyticsEvent)
                .filter_by(link_id=link.id, event_type="booked")
                .count()
            )

            conversion_rate = "0%"
            if total_views > 0:
                conversion_rate = f"{(total_bookings / total_views * 100):.1f}%"

            links_data.append(
                {
                    "id": str(link.id),
                    "owner_user_id": link.owner_user_id,
                    "slug": link.slug,
                    "is_active": link.is_active,
                    "settings": link.settings,
                    "template_id": str(link.template_id) if link.template_id else None,
                    "created_at": (
                        link.created_at.isoformat() if link.created_at else None
                    ),
                    "updated_at": (
                        link.updated_at.isoformat() if link.updated_at else None
                    ),
                    "total_views": total_views,
                    "total_bookings": total_bookings,
                    "conversion_rate": conversion_rate,
                }
            )

        return {
            "data": links_data,
            "total": len(links_data),
        }


@router.get("/links/{link_id}")
async def get_booking_link(
    link_id: str,
    request: Request = None,
    service_name: str = Depends(verify_api_key_auth),
) -> Dict[str, Any]:
    """Get a specific booking link"""
    # Rate limiting for authenticated endpoints
    if request:
        client_key = get_client_key(request)
        if not check_rate_limit(client_key, max_requests=100, window_seconds=3600):
            audit_logger.log_rate_limit_exceeded(
                client_key=client_key,
                endpoint=f"/links/{link_id}",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            raise RateLimitError(message="Rate limit exceeded")

    # Get authenticated user ID
    owner_user_id = get_user_id_from_request(request)

    # Database lookup
        with get_session() as session:
            link = (
                session.query(BookingLink)
                .filter_by(id=link_id, owner_user_id=owner_user_id)
                .first()
            )
            if not link:
                raise NotFoundError("Booking link", "not found")

        return {
            "data": {
                "id": str(link.id),
                "owner_user_id": link.owner_user_id,
                "slug": link.slug,
                "is_active": link.is_active,
                "settings": link.settings,
                "template_id": str(link.template_id) if link.template_id else None,
                "created_at": link.created_at.isoformat() if link.created_at else None,
                "updated_at": link.updated_at.isoformat() if link.updated_at else None,
            }
        }


@router.patch("/links/{link_id}")
async def update_booking_link(
    link_id: str,
    updates: dict,
    request: Request,
    service_name: str = Depends(verify_api_key_auth),
) -> Dict[str, Any]:
    """Update a booking link's settings"""
    # Rate limiting for authenticated endpoints
    client_key = get_client_key(request)
    if not check_rate_limit(client_key, max_requests=50, window_seconds=3600):
        audit_logger.log_rate_limit_exceeded(
            client_key=client_key,
            endpoint=f"/links/{link_id}",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        raise RateLimitError(message="Rate limit exceeded")

    # Get authenticated user ID
    owner_user_id = get_user_id_from_request(request)

    # Database update
    with get_session() as session:
        link = (
            session.query(BookingLink)
            .filter_by(id=link_id, owner_user_id=owner_user_id)
            .first()
        )
        if not link:
            raise NotFoundError(message="Booking link not found")

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
                user_id=owner_user_id,
                link_id=link_id,
                changes=changes,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )

        return {
            "data": {
                "id": str(link.id),
                "owner_user_id": link.owner_user_id,
                "slug": link.slug,
                "is_active": link.is_active,
                "settings": link.settings,
                "template_id": str(link.template_id) if link.template_id else None,
                "created_at": link.created_at.isoformat() if link.created_at else None,
                "updated_at": link.updated_at.isoformat() if link.updated_at else None,
            },
            "message": "Booking link updated successfully",
        }


@router.post("/links/{link_id}:duplicate")
async def duplicate_booking_link(
    link_id: str, request: Request, service_name: str = Depends(verify_api_key_auth)
):
    """Duplicate an existing booking link"""
    # Rate limiting for authenticated endpoints
    client_key = get_client_key(request)
    if not check_rate_limit(client_key, max_requests=20, window_seconds=3600):
        audit_logger.log_rate_limit_exceeded(
            client_key=client_key,
            endpoint=f"/links/{link_id}:duplicate",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        raise RateLimitError(message="Rate limit exceeded")

    # Get authenticated user ID
    owner_user_id = get_user_id_from_request(request)

    # Database duplication
    with get_session() as session:
        original = (
            session.query(BookingLink)
            .filter_by(id=link_id, owner_user_id=owner_user_id)
            .first()
        )
        if not original:
            raise NotFoundError(message="Booking link not found")

        # Generate unique slug
        new_slug = f"{original.slug}_copy_{TokenGenerator.generate_slug()[:4]}"
        existing_link = session.query(BookingLink).filter_by(slug=new_slug).first()
        counter = 1
        while existing_link:
            new_slug = (
                f"{original.slug}_copy_{TokenGenerator.generate_slug()[:4]}_{counter}"
            )
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
            user_id=owner_user_id,
            resource_id=link_id,
            details={"new_link_id": str(duplicated.id), "new_slug": new_slug},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        return {
            "data": {
                "id": str(duplicated.id),
                "slug": new_slug,
                "message": "Booking link duplicated successfully",
            }
        }


@router.post("/links/{link_id}:toggle")
async def toggle_booking_link(
    link_id: str, request: Request, service_name: str = Depends(verify_api_key_auth)
):
    """Toggle a booking link's active status"""
    # Rate limiting for authenticated endpoints
    client_key = get_client_key(request)
    if not check_rate_limit(client_key, max_requests=50, window_seconds=3600):
        audit_logger.log_rate_limit_exceeded(
            client_key=client_key,
            endpoint=f"/links/{link_id}:toggle",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        raise RateLimitError(message="Rate limit exceeded")

    # Get authenticated user ID
    owner_user_id = get_user_id_from_request(request)

    # Database toggle
    with get_session() as session:
        link = (
            session.query(BookingLink)
            .filter_by(id=link_id, owner_user_id=owner_user_id)
            .first()
        )
        if not link:
            raise NotFoundError(message="Booking link not found")

        old_status = link.is_active
        link.is_active = not link.is_active
        link.updated_at = datetime.now()
        session.commit()

        # Audit logging
        audit_logger.log_link_toggle(
            user_id=owner_user_id,
            link_id=link_id,
            new_status=link.is_active,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        return {
            "data": {
                "id": link_id,
                "is_active": link.is_active,
                "message": f"Booking link {'activated' if link.is_active else 'deactivated'} successfully",
            }
        }


@router.post("/links/{link_id}/one-time")
async def create_one_time_link(
    link_id: str,
    one_time_data: dict,
    request: Request,
    service_name: str = Depends(verify_api_key_auth),
):
    """Create a one-time link for a specific recipient"""
    # Rate limiting for authenticated endpoints
    client_key = get_client_key(request)
    if not check_rate_limit(client_key, max_requests=20, window_seconds=3600):
        audit_logger.log_rate_limit_exceeded(
            client_key=client_key,
            endpoint=f"/links/{link_id}/one-time",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        raise RateLimitError(message="Rate limit exceeded")

    # Get authenticated user ID
    owner_user_id = get_user_id_from_request(request)

    # Database creation
    with get_session() as session:
        link = (
            session.query(BookingLink)
            .filter_by(id=link_id, owner_user_id=owner_user_id)
            .first()
        )
        if not link:
            raise NotFoundError(message="Booking link not found")

        token = TokenGenerator.generate_one_time_token()
        expires_at = datetime.now() + timedelta(
            days=one_time_data.get("expires_in_days", 7)
        )

        # Sanitize recipient data
        recipient_email = SecurityUtils.sanitize_input(
            one_time_data.get("recipient_email", "")
        )
        recipient_name = SecurityUtils.sanitize_input(
            one_time_data.get("recipient_name", "")
        )

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
            user_id=owner_user_id,
            resource_id=link_id,
            details={
                "one_time_link_id": str(one_time_link.id),
                "recipient_email_hash": SecurityUtils.hash_email(recipient_email),
                "expires_at": expires_at.isoformat(),
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
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
async def get_link_analytics(
    link_id: str,
    request: Request = None,
    service_name: str = Depends(verify_api_key_auth),
):
    """Get analytics for a specific booking link"""
    # Rate limiting for authenticated endpoints
    if request:
        client_key = get_client_key(request)
        if not check_rate_limit(client_key, max_requests=100, window_seconds=3600):
            audit_logger.log_rate_limit_exceeded(
                client_key=client_key,
                endpoint=f"/links/{link_id}/analytics",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            raise RateLimitError(message="Rate limit exceeded")

    # Get authenticated user ID
    owner_user_id = get_user_id_from_request(request)

    # Database analytics calculation
    with get_session() as session:
        link = (
            session.query(BookingLink)
            .filter_by(id=link_id, owner_user_id=owner_user_id)
            .first()
        )
        if not link:
            raise NotFoundError(message="Booking link not found")

        # Get analytics data
        views = (
            session.query(AnalyticsEvent)
            .filter_by(link_id=link_id, event_type="view")
            .count()
        )

        bookings = (
            session.query(AnalyticsEvent)
            .filter_by(link_id=link_id, event_type="booked")
            .count()
        )

        conversion_rate = "0%"
        if views > 0:
            conversion_rate = f"{(bookings / views * 100):.1f}%"

        # Get recent activity
        recent_activity = (
            session.query(AnalyticsEvent)
            .filter_by(link_id=link_id)
            .order_by(AnalyticsEvent.occurred_at.desc())
            .limit(10)
            .all()
        )

        activity_data = []
        for event in recent_activity:
            activity_data.append(
                {
                    "type": event.event_type,
                    "timestamp": (
                        event.occurred_at.isoformat() if event.occurred_at else None
                    ),
                }
            )

        # Mock referrer data for now
        top_referrers = ["Direct", "Email", "LinkedIn"]

        analytics_data = {
            "link_id": link_id,
            "views": views,
            "bookings": bookings,
            "conversion_rate": conversion_rate,
            "last_viewed": (
                recent_activity[0].occurred_at.isoformat() if recent_activity else None
            ),
            "top_referrers": top_referrers,
            "recent_activity": activity_data,
        }

        # Audit logging
        if request:
            audit_logger.log_event(
                event_type=AuditEventType.ANALYTICS_VIEWED,
                user_id=owner_user_id,
                resource_id=link_id,
                details={"analytics_type": "link_performance"},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )

        return {"data": analytics_data}


# Template Management Endpoints
@router.post("/templates")
async def create_booking_template(
    template_data: dict,
    request: Request,
    service_name: str = Depends(verify_api_key_auth),
):
    """Create a new booking template"""
    # Rate limiting for authenticated endpoints
    client_key = get_client_key(request)
    if not check_rate_limit(client_key, max_requests=50, window_seconds=3600):
        audit_logger.log_rate_limit_exceeded(
            client_key=client_key,
            endpoint="/templates",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        raise RateLimitError(message="Rate limit exceeded")

    # Get authenticated user ID
    owner_user_id = get_user_id_from_request(request)

    # Sanitize input
    name = SecurityUtils.sanitize_input(template_data.get("name", ""))
    questions = template_data.get("questions", [])

    # Validate required fields
    if not name:
        raise ValidationError(message="Template name is required")

    # Database creation
    with get_session() as session:
        template = BookingTemplate(
            owner_user_id=owner_user_id,
            name=name,
            questions=questions,
            email_followup_enabled=template_data.get("email_followup_enabled", False),
        )

        session.add(template)
        session.commit()
        session.refresh(template)

        # Audit logging
        audit_logger.log_event(
            event_type=AuditEventType.TEMPLATE_CREATED,
            user_id=owner_user_id,
            resource_id=str(template.id),
            details={"template_name": name, "questions_count": len(questions)},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        return {
            "data": {
                "id": str(template.id),
                "name": template.name,
                "questions": template.questions,
                "email_followup_enabled": template.email_followup_enabled,
                "created_at": (
                    template.created_at.isoformat() if template.created_at else None
                ),
                "message": "Template created successfully",
            }
        }


@router.get("/templates")
async def list_booking_templates(
    request: Request = None, service_name: str = Depends(verify_api_key_auth)
):
    """List all booking templates for the authenticated user"""
    # Rate limiting for authenticated endpoints
    if request:
        client_key = get_client_key(request)
        if not check_rate_limit(client_key, max_requests=100, window_seconds=3600):
            audit_logger.log_rate_limit_exceeded(
                client_key=client_key,
                endpoint="/templates",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            raise RateLimitError(message="Rate limit exceeded")

    # Get authenticated user ID
    owner_user_id = get_user_id_from_request(request)

    # Database query
    with get_session() as session:
        templates = (
            session.query(BookingTemplate).filter_by(owner_user_id=owner_user_id).all()
        )

        templates_data = []
        for template in templates:
            # Count how many links use this template
            links_using_template = (
                session.query(BookingLink).filter_by(template_id=template.id).count()
            )

            templates_data.append(
                {
                    "id": str(template.id),
                    "name": template.name,
                    "questions": template.questions,
                    "email_followup_enabled": template.email_followup_enabled,
                    "created_at": (
                        template.created_at.isoformat() if template.created_at else None
                    ),
                    "updated_at": (
                        template.updated_at.isoformat() if template.updated_at else None
                    ),
                    "links_using_template": links_using_template,
                }
            )

        return {
            "data": templates_data,
            "total": len(templates_data),
        }


@router.get("/templates/{template_id}")
async def get_booking_template(
    template_id: str,
    request: Request = None,
    service_name: str = Depends(verify_api_key_auth),
):
    """Get a specific booking template"""
    # Rate limiting for authenticated endpoints
    if request:
        client_key = get_client_key(request)
        if not check_rate_limit(client_key, max_requests=100, window_seconds=3600):
            audit_logger.log_rate_limit_exceeded(
                client_key=client_key,
                endpoint=f"/templates/{template_id}",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            raise RateLimitError(message="Rate limit exceeded")

    # Get authenticated user ID
    owner_user_id = get_user_id_from_request(request)

    # Database lookup
    with get_session() as session:
        template = (
            session.query(BookingTemplate)
            .filter_by(id=template_id, owner_user_id=owner_user_id)
            .first()
        )
        if not template:
            raise NotFoundError(message="Template not found")

        return {
            "data": {
                "id": str(template.id),
                "name": template.name,
                "questions": template.questions,
                "email_followup_enabled": template.email_followup_enabled,
                "created_at": (
                    template.created_at.isoformat() if template.created_at else None
                ),
                "updated_at": (
                    template.updated_at.isoformat() if template.updated_at else None
                ),
            }
        }


@router.patch("/templates/{template_id}")
async def update_booking_template(
    template_id: str,
    updates: dict,
    request: Request,
    service_name: str = Depends(verify_api_key_auth),
):
    """Update a booking template"""
    # Rate limiting for authenticated endpoints
    client_key = get_client_key(request)
    if not check_rate_limit(client_key, max_requests=50, window_seconds=3600):
        audit_logger.log_rate_limit_exceeded(
            client_key=client_key,
            endpoint=f"/templates/{template_id}",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        raise RateLimitError(message="Rate limit exceeded")

    # Get authenticated user ID
    owner_user_id = get_user_id_from_request(request)

    # Database update
    with get_session() as session:
        template = (
            session.query(BookingTemplate)
            .filter_by(id=template_id, owner_user_id=owner_user_id)
            .first()
        )
        if not template:
            raise NotFoundError(message="Template not found")

        # Track changes for audit logging
        changes = {}

        # Update fields
        if "name" in updates:
            old_name = template.name
            template.name = SecurityUtils.sanitize_input(updates["name"])
            changes["name"] = {"old": old_name, "new": template.name}

        if "questions" in updates:
            old_questions = template.questions
            template.questions = updates["questions"]
            changes["questions"] = {"old": old_questions, "new": template.questions}

        if "email_followup_enabled" in updates:
            old_followup = template.email_followup_enabled
            template.email_followup_enabled = updates["email_followup_enabled"]
            changes["email_followup_enabled"] = {
                "old": old_followup,
                "new": template.email_followup_enabled,
            }

        template.updated_at = datetime.now()
        session.commit()

        # Audit logging
        if changes:
            audit_logger.log_event(
                event_type=AuditEventType.TEMPLATE_UPDATED,
                user_id=owner_user_id,
                resource_id=template_id,
                details={"changes": changes},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )

        return {
            "data": {
                "id": str(template.id),
                "name": template.name,
                "questions": template.questions,
                "email_followup_enabled": template.email_followup_enabled,
                "created_at": (
                    template.created_at.isoformat() if template.created_at else None
                ),
                "updated_at": (
                    template.updated_at.isoformat() if template.updated_at else None
                ),
            },
            "message": "Template updated successfully",
        }


@router.delete("/templates/{template_id}")
async def delete_booking_template(
    template_id: str, request: Request, service_name: str = Depends(verify_api_key_auth)
):
    """Delete a booking template"""
    # Rate limiting for authenticated endpoints
    client_key = get_client_key(request)
    if not check_rate_limit(client_key, max_requests=20, window_seconds=3600):
        audit_logger.log_rate_limit_exceeded(
            client_key=client_key,
            endpoint=f"/templates/{template_id}",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        raise RateLimitError(message="Rate limit exceeded")

    # Get authenticated user ID
    owner_user_id = get_user_id_from_request(request)

    # Database deletion
    with get_session() as session:
        template = (
            session.query(BookingTemplate)
            .filter_by(id=template_id, owner_user_id=owner_user_id)
            .first()
        )
        if not template:
            raise NotFoundError(message="Template not found")

        # Check if template is being used by any links
        links_using_template = (
            session.query(BookingLink).filter_by(template_id=template_id).count()
        )
        if links_using_template > 0:
            raise ServiceError(
                message=f"Cannot delete template: {links_using_template} booking link(s) are using it"
            )

        # Store template info for audit logging
        template_name = template.name

        session.delete(template)
        session.commit()

        # Audit logging
        audit_logger.log_event(
            event_type=AuditEventType.TEMPLATE_DELETED,
            user_id=owner_user_id,
            resource_id=template_id,
            details={"template_name": template_name},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        return {"message": "Template deleted successfully"}


# One-time Link Management Endpoints
@router.get("/links/{link_id}/one-time")
async def list_one_time_links(
    link_id: str,
    request: Request = None,
    service_name: str = Depends(verify_api_key_auth),
):
    """List all one-time links for a specific booking link"""
    # Rate limiting for authenticated endpoints
    if request:
        client_key = get_client_key(request)
        if not check_rate_limit(client_key, max_requests=100, window_seconds=3600):
            audit_logger.log_rate_limit_exceeded(
                client_key=client_key,
                endpoint=f"/links/{link_id}/one-time",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            raise RateLimitError(message="Rate limit exceeded")

    # Get authenticated user ID
    owner_user_id = get_user_id_from_request(request)

    # Database query
    with get_session() as session:
        # Verify the user owns the booking link
        link = (
            session.query(BookingLink)
            .filter_by(id=link_id, owner_user_id=owner_user_id)
            .first()
        )
        if not link:
            raise NotFoundError(message="Booking link not found")

        # Get all one-time links for this booking link
        one_time_links = (
            session.query(OneTimeLink).filter_by(booking_link_id=link_id).all()
        )

        links_data = []
        for one_time_link in one_time_links:
            # Check if expired
            is_expired = (
                one_time_link.expires_at and one_time_link.expires_at < datetime.now()
            )

            links_data.append(
                {
                    "id": str(one_time_link.id),
                    "recipient_email": one_time_link.recipient_email,
                    "recipient_name": one_time_link.recipient_name,
                    "token": one_time_link.token,
                    "expires_at": (
                        one_time_link.expires_at.isoformat()
                        if one_time_link.expires_at
                        else None
                    ),
                    "status": one_time_link.status,
                    "created_at": (
                        one_time_link.created_at.isoformat()
                        if one_time_link.created_at
                        else None
                    ),
                    "is_expired": is_expired,
                    "public_url": f"/public/bookings/{one_time_link.token}",
                }
            )

        return {
            "data": links_data,
            "total": len(links_data),
        }


@router.get("/one-time/{token}")
async def get_one_time_link_details(
    token: str,
    request: Request = None,
    service_name: str = Depends(verify_api_key_auth),
):
    """Get details of a one-time link (for owner)"""
    # Rate limiting for authenticated endpoints
    if request:
        client_key = get_client_key(request)
        if not check_rate_limit(client_key, max_requests=100, window_seconds=3600):
            audit_logger.log_rate_limit_exceeded(
                client_key=client_key,
                endpoint=f"/one-time/{token}",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            raise RateLimitError(message="Rate limit exceeded")

    # Get authenticated user ID
    owner_user_id = get_user_id_from_request(request)

    # Database lookup
    with get_session() as session:
        one_time_link = session.query(OneTimeLink).filter_by(token=token).first()
        if not one_time_link:
            raise NotFoundError(message="One-time link not found")

        # Verify the user owns the parent booking link
        booking_link = (
            session.query(BookingLink)
            .filter_by(id=one_time_link.booking_link_id, owner_user_id=owner_user_id)
            .first()
        )
        if not booking_link:
            raise AuthError(message="Not authorized to view this one-time link")

        # Check if expired
        is_expired = (
            one_time_link.expires_at and one_time_link.expires_at < datetime.now()
        )

        return {
            "data": {
                "id": str(one_time_link.id),
                "recipient_email": one_time_link.recipient_email,
                "recipient_name": one_time_link.recipient_name,
                "token": one_time_link.token,
                "expires_at": (
                    one_time_link.expires_at.isoformat()
                    if one_time_link.expires_at
                    else None
                ),
                "status": one_time_link.status,
                "created_at": (
                    one_time_link.created_at.isoformat()
                    if one_time_link.created_at
                    else None
                ),
                "is_expired": is_expired,
                "public_url": f"/public/bookings/{one_time_link.token}",
                "parent_link_id": str(one_time_link.booking_link_id),
            }
        }


@router.patch("/one-time/{token}")
async def update_one_time_link(
    token: str,
    updates: dict,
    request: Request,
    service_name: str = Depends(verify_api_key_auth),
):
    """Update a one-time link"""
    # Rate limiting for authenticated endpoints
    client_key = get_client_key(request)
    if not check_rate_limit(client_key, max_requests=50, window_seconds=3600):
        audit_logger.log_rate_limit_exceeded(
            client_key=client_key,
            endpoint=f"/one-time/{token}",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        raise RateLimitError(message="Rate limit exceeded")

    # Get authenticated user ID
    owner_user_id = get_user_id_from_request(request)

    # Database update
    with get_session() as session:
        one_time_link = session.query(OneTimeLink).filter_by(token=token).first()
        if not one_time_link:
            raise NotFoundError(message="One-time link not found")

        # Verify the user owns the parent booking link
        booking_link = (
            session.query(BookingLink)
            .filter_by(id=one_time_link.booking_link_id, owner_user_id=owner_user_id)
            .first()
        )
        if not booking_link:
            raise AuthError(message="Not authorized to update this one-time link")

        # Track changes for audit logging
        changes = {}

        # Update fields
        if "recipient_email" in updates:
            old_email = one_time_link.recipient_email
            one_time_link.recipient_email = SecurityUtils.sanitize_input(
                updates["recipient_email"]
            )
            changes["recipient_email"] = {
                "old": old_email,
                "new": one_time_link.recipient_email,
            }

        if "recipient_name" in updates:
            old_name = one_time_link.recipient_name
            one_time_link.recipient_name = SecurityUtils.sanitize_input(
                updates["recipient_name"]
            )
            changes["recipient_name"] = {
                "old": old_name,
                "new": one_time_link.recipient_name,
            }

        if "expires_at" in updates:
            old_expires = one_time_link.expires_at
            new_expires = datetime.fromisoformat(updates["expires_at"])
            one_time_link.expires_at = new_expires
            changes["expires_at"] = {
                "old": old_expires.isoformat() if old_expires else None,
                "new": new_expires.isoformat(),
            }

        if "status" in updates:
            old_status = one_time_link.status
            one_time_link.status = updates["status"]
            changes["status"] = {"old": old_status, "new": one_time_link.status}

        session.commit()

        # Audit logging
        if changes:
            audit_logger.log_event(
                event_type=AuditEventType.ONE_TIME_LINK_UPDATED,
                user_id=owner_user_id,
                resource_id=str(one_time_link.id),
                details={"changes": changes},
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )

        return {
            "data": {
                "id": str(one_time_link.id),
                "recipient_email": one_time_link.recipient_email,
                "recipient_name": one_time_link.recipient_name,
                "token": one_time_link.token,
                "expires_at": (
                    one_time_link.expires_at.isoformat()
                    if one_time_link.expires_at
                    else None
                ),
                "status": one_time_link.status,
                "created_at": (
                    one_time_link.created_at.isoformat()
                    if one_time_link.created_at
                    else None
                ),
                "public_url": f"/public/bookings/{one_time_link.token}",
            },
            "message": "One-time link updated successfully",
        }


@router.delete("/one-time/{token}")
async def delete_one_time_link(
    token: str, request: Request, service_name: str = Depends(verify_api_key_auth)
):
    """Delete a one-time link"""
    # Rate limiting for authenticated endpoints
    client_key = get_client_key(request)
    if not check_rate_limit(client_key, max_requests=20, window_seconds=3600):
        audit_logger.log_rate_limit_exceeded(
            client_key=client_key,
            endpoint=f"/one-time/{token}",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        raise RateLimitError(message="Rate limit exceeded")

    # Get authenticated user ID
    owner_user_id = get_user_id_from_request(request)

    # Database deletion
    with get_session() as session:
        one_time_link = session.query(OneTimeLink).filter_by(token=token).first()
        if not one_time_link:
            raise NotFoundError(message="One-time link not found")

        # Verify the user owns the parent booking link
        booking_link = (
            session.query(BookingLink)
            .filter_by(id=one_time_link.booking_link_id, owner_user_id=owner_user_id)
            .first()
        )
        if not booking_link:
            raise AuthError(message="Not authorized to delete this one-time link")

        # Store info for audit logging
        recipient_email = one_time_link.recipient_email
        recipient_name = one_time_link.recipient_name

        session.delete(one_time_link)
        session.commit()

        # Audit logging
        audit_logger.log_event(
            event_type=AuditEventType.ONE_TIME_LINK_DELETED,
            user_id=owner_user_id,
            resource_id=str(one_time_link.id),
            details={
                "recipient_email_hash": SecurityUtils.hash_email(recipient_email),
                "recipient_name": recipient_name,
                "parent_link_id": str(one_time_link.booking_link_id),
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        return {"message": "One-time link deleted successfully"}
