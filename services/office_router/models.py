#!/usr/bin/env python3
"""
Data models for the office router service
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

class DownstreamService(BaseModel):
    """Configuration for a downstream service"""
    name: str
    endpoint: str
    enabled: bool = True
    timeout: int = 30
    
    class Config:
        extra = "forbid"

class RoutingResult(BaseModel):
    """Result of routing data to downstream services"""
    timestamp: str
    source_data_id: Optional[str]
    results: Dict[str, Dict[str, Any]]
    
    class Config:
        extra = "forbid"

class EmailData(BaseModel):
    """Email data structure for routing"""
    id: str
    user_id: str
    provider: str  # "microsoft" or "google"
    type: str = "email"
    subject: str
    body: str
    from_: str = Field(alias="from")
    to: List[str] = []
    cc: List[str] = []
    bcc: List[str] = []
    thread_id: Optional[str] = None
    folder: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    attachments: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}
    
    class Config:
        allow_population_by_field_name = True
        extra = "forbid"

class CalendarData(BaseModel):
    """Calendar event data structure for routing"""
    id: str
    user_id: str
    provider: str
    type: str = "calendar"
    subject: str
    body: Optional[str] = None
    start_time: datetime
    end_time: datetime
    attendees: List[str] = []
    location: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}
    
    class Config:
        extra = "forbid"

class ContactData(BaseModel):
    """Contact data structure for routing"""
    id: str
    user_id: str
    provider: str
    type: str = "contact"
    display_name: str
    email_addresses: List[str] = []
    phone_numbers: List[str] = []
    company: Optional[str] = None
    job_title: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}
    
    class Config:
        extra = "forbid"

class ServiceHealth(BaseModel):
    """Health status of a downstream service"""
    name: str
    status: str  # "healthy", "unhealthy", "unknown"
    response_time_ms: Optional[float] = None
    last_check: datetime
    error_message: Optional[str] = None
    
    class Config:
        extra = "forbid"

class RouterStatus(BaseModel):
    """Overall status of the office router"""
    service_name: str = "office-router"
    version: str = "1.0.0"
    status: str = "running"
    uptime_seconds: float
    downstream_services: Dict[str, ServiceHealth]
    total_routed: int
    successful_routes: int
    failed_routes: int
    
    class Config:
        extra = "forbid"
