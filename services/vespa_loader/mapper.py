#!/usr/bin/env python3
"""
Document mapper for transforming office service data to Vespa format
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class DocumentMapper:
    """Maps office service data formats to Vespa document format"""
    
    def __init__(self):
        # Field mappings from office service to Vespa
        self.field_mappings = {
            "email": {
                "id": "doc_id",
                "subject": "title",
                "body": "content",
                "from": "sender",
                "to": "recipients",
                "thread_id": "thread_id",
                "folder": "folder",
                "created_at": "created_at",
                "updated_at": "updated_at"
            },
            "calendar": {
                "id": "doc_id",
                "subject": "title",
                "body": "content",
                "start_time": "start_time",
                "end_time": "end_time",
                "attendees": "attendees",
                "location": "location",
                "created_at": "created_at",
                "updated_at": "updated_at"
            },
            "contact": {
                "id": "doc_id",
                "display_name": "title",
                "email_addresses": "email_addresses",
                "phone_numbers": "phone_numbers",
                "company": "company",
                "job_title": "job_title",
                "created_at": "created_at",
                "updated_at": "updated_at"
            },
            "file": {
                "id": "doc_id",
                "name": "title",
                "content": "content",
                "file_type": "file_type",
                "size": "size",
                "created_at": "created_at",
                "updated_at": "updated_at"
            }
        }
    
    def map_to_vespa(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map office service document to Vespa format"""
        try:
            # Determine document type
            doc_type = self._determine_document_type(document_data)
            
            # Get field mappings for this type
            mappings = self.field_mappings.get(doc_type, {})
            
            # Create Vespa document
            vespa_doc = {
                "user_id": document_data.get("user_id"),
                "doc_id": document_data.get("id"),
                "provider": document_data.get("provider"),
                "source_type": doc_type,
                "title": "",
                "content": "",
                "search_text": "",
                "sender": "",
                "recipients": [],
                "thread_id": "",
                "folder": "",
                "created_at": None,
                "updated_at": None,
                "metadata": {}
            }
            
            # Map fields according to type
            vespa_doc = self._map_fields(document_data, vespa_doc, mappings)
            
            # Generate search text
            vespa_doc["search_text"] = self._generate_search_text(vespa_doc, doc_type)
            
            # Add metadata
            vespa_doc["metadata"] = self._extract_metadata(document_data, doc_type)
            
            # Validate required fields
            self._validate_vespa_document(vespa_doc)
            
            return vespa_doc
            
        except Exception as e:
            logger.error(f"Error mapping document to Vespa format: {e}")
            raise
    
    def _determine_document_type(self, document_data: Dict[str, Any]) -> str:
        """Determine the type of document based on content"""
        # Check explicit type field
        if "type" in document_data:
            return document_data["type"]
        
        # Infer type from content
        if "subject" in document_data and "body" in document_data:
            return "email"
        elif "start_time" in document_data and "end_time" in document_data:
            return "calendar"
        elif "display_name" in document_data and "email_addresses" in document_data:
            return "contact"
        elif "name" in document_data and "file_type" in document_data:
            return "file"
        else:
            # Default to email if we can't determine
            return "email"
    
    def _map_fields(self, source: Dict[str, Any], target: Dict[str, Any], 
                    mappings: Dict[str, str]) -> Dict[str, Any]:
        """Map fields from source to target using the provided mappings"""
        for source_field, target_field in mappings.items():
            if source_field in source:
                target[target_field] = source[source_field]
        
        return target
    
    def _generate_search_text(self, vespa_doc: Dict[str, Any], doc_type: str) -> str:
        """Generate search text for the document"""
        search_parts = []
        
        # Add title
        if vespa_doc.get("title"):
            search_parts.append(vespa_doc["title"])
        
        # Add content
        if vespa_doc.get("content"):
            search_parts.append(vespa_doc["content"])
        
        # Add type-specific fields
        if doc_type == "email":
            if vespa_doc.get("sender"):
                search_parts.append(f"From: {vespa_doc['sender']}")
            if vespa_doc.get("recipients"):
                search_parts.append(f"To: {', '.join(vespa_doc['recipients'])}")
        
        elif doc_type == "calendar":
            if vespa_doc.get("attendees"):
                search_parts.append(f"Attendees: {', '.join(vespa_doc['attendees'])}")
            if vespa_doc.get("location"):
                search_parts.append(f"Location: {vespa_doc['location']}")
        
        elif doc_type == "contact":
            if vespa_doc.get("company"):
                search_parts.append(f"Company: {vespa_doc['company']}")
            if vespa_doc.get("job_title"):
                search_parts.append(f"Job: {vespa_doc['job_title']}")
        
        # Join all parts
        search_text = " ".join(search_parts)
        
        # Truncate if too long
        if len(search_text) > 10000:
            search_text = search_text[:10000] + "..."
        
        return search_text
    
    def _extract_metadata(self, document_data: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
        """Extract metadata from the document"""
        metadata = {}
        
        # Common metadata
        if "metadata" in document_data:
            metadata.update(document_data["metadata"])
        
        # Type-specific metadata
        if doc_type == "email":
            metadata.update({
                "has_attachments": bool(document_data.get("attachments")),
                "attachment_count": len(document_data.get("attachments", [])),
                "is_reply": bool(document_data.get("in_reply_to")),
                "is_forward": bool(document_data.get("forwarded_from"))
            })
        
        elif doc_type == "calendar":
            metadata.update({
                "is_all_day": document_data.get("is_all_day", False),
                "is_recurring": bool(document_data.get("recurrence_pattern")),
                "attendee_count": len(document_data.get("attendees", [])),
                "has_location": bool(document_data.get("location"))
            })
        
        elif doc_type == "contact":
            metadata.update({
                "email_count": len(document_data.get("email_addresses", [])),
                "phone_count": len(document_data.get("phone_numbers", [])),
                "has_company": bool(document_data.get("company")),
                "has_job_title": bool(document_data.get("job_title"))
            })
        
        elif doc_type == "file":
            metadata.update({
                "file_extension": document_data.get("file_extension"),
                "mime_type": document_data.get("mime_type"),
                "is_shared": document_data.get("is_shared", False),
                "permissions": document_data.get("permissions", [])
            })
        
        return metadata
    
    def _validate_vespa_document(self, vespa_doc: Dict[str, Any]):
        """Validate that the Vespa document has required fields"""
        required_fields = ["user_id", "doc_id", "provider", "source_type"]
        
        for field in required_fields:
            if not vespa_doc.get(field):
                raise ValueError(f"Missing required field: {field}")
        
        # Ensure user_id is a string
        if not isinstance(vespa_doc["user_id"], str):
            raise ValueError("user_id must be a string")
        
        # Ensure doc_id is a string
        if not isinstance(vespa_doc["doc_id"], str):
            raise ValueError("doc_id must be a string")
        
        # Ensure provider is a string
        if not isinstance(vespa_doc["provider"], str):
            raise ValueError("provider must be a string")
        
        # Ensure source_type is a string
        if not isinstance(vespa_doc["source_type"], str):
            raise ValueError("source_type must be a string")
    
    def map_from_vespa(self, vespa_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Map Vespa document back to office service format"""
        try:
            doc_type = vespa_doc.get("source_type", "email")
            
            # Get reverse field mappings
            reverse_mappings = {v: k for k, v in self.field_mappings.get(doc_type, {}).items()}
            
            # Create office service document
            office_doc = {
                "id": vespa_doc.get("doc_id"),
                "user_id": vespa_doc.get("user_id"),
                "provider": vespa_doc.get("provider"),
                "type": doc_type
            }
            
            # Map fields back
            for vespa_field, office_field in reverse_mappings.items():
                if vespa_field in vespa_doc:
                    office_doc[office_field] = vespa_doc[vespa_field]
            
            # Add metadata
            if vespa_doc.get("metadata"):
                office_doc["metadata"] = vespa_doc["metadata"]
            
            return office_doc
            
        except Exception as e:
            logger.error(f"Error mapping Vespa document to office service format: {e}")
            raise
