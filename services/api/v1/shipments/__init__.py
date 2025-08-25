"""
Shipments service API schemas.
"""

from services.api.v1.shipments import email_parser, pagination

__all__ = ["email_parser", "pagination"]
