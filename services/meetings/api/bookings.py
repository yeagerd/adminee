from fastapi import APIRouter, HTTPException, Depends
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

router = APIRouter()

# Mock database for now - replace with actual database operations
mock_booking_links = []
mock_booking_templates = []
mock_bookings = []
mock_analytics_events = []

@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "bookings"}

@router.get("/public/{token}")
async def get_public_link(token: str):
    """Get public link metadata including template questions"""
    # TODO: Replace with actual database lookup
    if not token.startswith("ot_") and not token.startswith("bl_"):
        raise HTTPException(status_code=404, detail="Invalid token format")
    
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
async def get_public_availability(token: str, duration: int = 30):
    """Get available time slots for a public link"""
    # TODO: Replace with actual availability calculation
    if not token.startswith("ot_") and not token.startswith("bl_"):
        raise HTTPException(status_code=404, detail="Invalid token format")
    
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
async def create_public_booking(token: str, booking_data: dict):
    """Create a booking from a public link"""
    # TODO: Replace with actual booking creation logic
    if not token.startswith("ot_") and not token.startswith("bl_"):
        raise HTTPException(status_code=404, detail="Invalid token format")
    
    # Validate required fields
    required_fields = ["start", "end", "attendeeEmail"]
    for field in required_fields:
        if field not in booking_data:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    
    # Mock booking creation
    booking_id = str(uuid.uuid4())
    mock_booking = {
        "id": booking_id,
        "token": token,
        "start_at": booking_data["start"],
        "end_at": booking_data["end"],
        "attendee_email": booking_data["attendeeEmail"],
        "answers": booking_data.get("answers", {}),
        "created_at": datetime.now().isoformat(),
    }
    
    mock_bookings.append(mock_booking)
    
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
async def create_booking_link(link_data: dict):
    """Create a new evergreen booking link"""
    # TODO: Replace with actual database creation
    link_id = str(uuid.uuid4())
    slug = link_data.get("slug") or f"bl_{uuid.uuid4().hex[:8]}"
    
    new_link = {
        "id": link_id,
        "owner_user_id": "mock_user_id",  # TODO: Get from auth
        "slug": slug,
        "title": link_data.get("title", ""),
        "description": link_data.get("description", ""),
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
    
    return {
        "data": {
            "id": link_id,
            "slug": slug,
            "public_url": f"/public/bookings/{slug}",
            "message": "Booking link created successfully",
        }
    }

@router.get("/links")
async def list_booking_links():
    """List all booking links for the authenticated user"""
    # TODO: Replace with actual database query
    return {
        "data": mock_booking_links,
        "total": len(mock_booking_links),
    }

@router.get("/links/{link_id}")
async def get_booking_link(link_id: str):
    """Get a specific booking link"""
    # TODO: Replace with actual database lookup
    link = next((l for l in mock_booking_links if l["id"] == link_id), None)
    if not link:
        raise HTTPException(status_code=404, detail="Booking link not found")
    
    return {"data": link}

@router.patch("/links/{link_id}")
async def update_booking_link(link_id: str, updates: dict):
    """Update a booking link's settings"""
    # TODO: Replace with actual database update
    link = next((l for l in mock_booking_links if l["id"] == link_id), None)
    if not link:
        raise HTTPException(status_code=404, detail="Booking link not found")
    
    # Update fields
    for key, value in updates.items():
        if key in link:
            link[key] = value
        elif key in link.get("settings", {}):
            link["settings"][key] = value
    
    link["updated_at"] = datetime.now().isoformat()
    
    return {"data": link, "message": "Booking link updated successfully"}

@router.post("/links/{link_id}:duplicate")
async def duplicate_booking_link(link_id: str):
    """Duplicate an existing booking link"""
    # TODO: Replace with actual database duplication
    original = next((l for l in mock_booking_links if l["id"] == link_id), None)
    if not original:
        raise HTTPException(status_code=404, detail="Booking link not found")
    
    new_id = str(uuid.uuid4())
    new_slug = f"{original['slug']}_copy_{uuid.uuid4().hex[:4]}"
    
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
    
    return {
        "data": {
            "id": new_id,
            "slug": new_slug,
            "message": "Booking link duplicated successfully",
        }
    }

@router.post("/links/{link_id}:toggle")
async def toggle_booking_link(link_id: str):
    """Toggle a booking link's active status"""
    # TODO: Replace with actual database toggle
    link = next((l for l in mock_booking_links if l["id"] == link_id), None)
    if not link:
        raise HTTPException(status_code=404, detail="Booking link not found")
    
    link["is_active"] = not link["is_active"]
    link["updated_at"] = datetime.now().isoformat()
    
    return {
        "data": {
            "id": link_id,
            "is_active": link["is_active"],
            "message": f"Booking link {'activated' if link['is_active'] else 'deactivated'} successfully",
        }
    }

@router.post("/links/{link_id}/one-time")
async def create_one_time_link(link_id: str, one_time_data: dict):
    """Create a one-time link for a specific recipient"""
    # TODO: Replace with actual database creation
    link = next((l for l in mock_booking_links if l["id"] == link_id), None)
    if not link:
        raise HTTPException(status_code=404, detail="Booking link not found")
    
    token = f"ot_{uuid.uuid4().hex[:12]}"
    expires_at = datetime.now() + timedelta(days=one_time_data.get("expires_in_days", 7))
    
    one_time_link = {
        "id": str(uuid.uuid4()),
        "booking_link_id": link_id,
        "recipient_email": one_time_data.get("recipient_email"),
        "recipient_name": one_time_data.get("recipient_name"),
        "token": token,
        "expires_at": expires_at.isoformat(),
        "status": "active",
        "created_at": datetime.now().isoformat(),
    }
    
    # TODO: Store in database
    
    return {
        "data": {
            "token": token,
            "public_url": f"/public/bookings/{token}",
            "expires_at": expires_at.isoformat(),
            "message": "One-time link created successfully",
        }
    }

@router.get("/links/{link_id}/analytics")
async def get_link_analytics(link_id: str):
    """Get analytics for a specific booking link"""
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
    
    return {"data": mock_analytics}


