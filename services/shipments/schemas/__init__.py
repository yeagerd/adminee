"""
Pydantic schemas for the shipments service
"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class LabelOut(BaseModel):
    id: int
    name: str
    color: str
    created_at: datetime


class PackageOut(BaseModel):
    id: int
    tracking_number: str
    carrier: str
    status: str
    estimated_delivery: Optional[date]
    actual_delivery: Optional[date]
    recipient_name: Optional[str]
    shipper_name: Optional[str]
    package_description: Optional[str]
    order_number: Optional[str]
    tracking_link: Optional[str]
    last_updated: datetime = Field(..., alias="updated_at")
    events_count: int
    labels: List[LabelOut]


class PackageCreate(BaseModel):
    tracking_number: str
    carrier: str
    status: Optional[str] = "pending"
    estimated_delivery: Optional[date]
    recipient_name: Optional[str]
    shipper_name: Optional[str]
    package_description: Optional[str]
    order_number: Optional[str]
    tracking_link: Optional[str]
    email_message_id: Optional[str]


class PackageUpdate(BaseModel):
    status: Optional[str]
    estimated_delivery: Optional[date]
    actual_delivery: Optional[date]
    recipient_name: Optional[str]
    shipper_name: Optional[str]
    package_description: Optional[str]
    order_number: Optional[str]
    tracking_link: Optional[str]
    archived_at: Optional[datetime]


class TrackingEventOut(BaseModel):
    id: int
    event_date: datetime
    status: str
    location: Optional[str]
    description: Optional[str]
    created_at: datetime


class TrackingEventCreate(BaseModel):
    event_date: datetime
    status: str
    location: Optional[str]
    description: Optional[str]


class LabelCreate(BaseModel):
    name: str
    color: Optional[str] = "#3B82F6"


class LabelUpdate(BaseModel):
    name: Optional[str]
    color: Optional[str]


class PackageLabelOut(BaseModel):
    id: int
    package_id: int
    label_id: int
    created_at: datetime


class CarrierConfigOut(BaseModel):
    id: int
    carrier_name: str
    api_endpoint: Optional[str]
    rate_limit_per_hour: int
    is_active: bool
    email_patterns: Optional[str]
    created_at: datetime


class Pagination(BaseModel):
    page: int
    per_page: int
    total: int


class PackageListResponse(BaseModel):
    data: List[PackageOut]
    pagination: Pagination
