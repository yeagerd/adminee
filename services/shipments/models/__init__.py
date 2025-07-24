"""
Database models for the shipments service
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel


class PackageLabel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    package_id: int = Field(foreign_key="package.id")
    label_id: int = Field(foreign_key="label.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Package(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    tracking_number: str = Field(max_length=255)
    carrier: str = Field(max_length=50)
    status: str = Field(max_length=50)
    estimated_delivery: Optional[date] = None
    actual_delivery: Optional[date] = None
    recipient_name: Optional[str] = Field(default=None, max_length=255)
    recipient_address: Optional[str] = None
    shipper_name: Optional[str] = Field(default=None, max_length=255)
    package_description: Optional[str] = None
    order_number: Optional[str] = Field(default=None, max_length=255)
    tracking_link: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    archived_at: Optional[datetime] = None
    email_message_id: Optional[str] = Field(default=None, max_length=255)

    if TYPE_CHECKING:
        from services.shipments.models import Label, Package, TrackingEvent

    tracking_events: List["TrackingEvent"] = Relationship(back_populates="package")
    labels: List["Label"] = Relationship(
        back_populates="packages", link_model=PackageLabel
    )

    __table_args__ = ({"sqlite_autoincrement": True},)


class Label(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    name: str = Field(max_length=100)
    color: str = Field(default="#3B82F6", max_length=7)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    if TYPE_CHECKING:
        from services.shipments.models import Package

    packages: List["Package"] = Relationship(
        back_populates="labels", link_model=PackageLabel
    )


class TrackingEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    package_id: int = Field(foreign_key="package.id")
    event_date: datetime
    status: str = Field(max_length=100)
    location: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    package: Optional["Package"] = Relationship(back_populates="tracking_events")


class CarrierConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    carrier_name: str = Field(max_length=50)
    api_endpoint: Optional[str] = Field(default=None, max_length=255)
    rate_limit_per_hour: int = Field(default=1000)
    is_active: bool = Field(default=True)
    email_patterns: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
