#!/usr/bin/env python3
"""
Document mapper for transforming office service data to Vespa format
"""

from typing import Dict, Any, Optional
from datetime import datetime
from services.common.logging_config import get_logger

logger = get_logger(__name__)

class DocumentMapper:
    """Maps office service data formats to Vespa document format"""
    
    def __init__(self) -> None:
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
            vespa_doc: Dict[str, Any] = {
                # Remove id field - Vespa streaming mode generates this automatically from URL path
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
        # Check for email-specific fields
        if "subject" in document_data and "body" in document_data:
            return "email"
        
        # Check for calendar-specific fields
        if "start_time" in document_data and "end_time" in document_data:
            return "calendar"
        
        # Check for contact-specific fields
        if "display_name" in document_data and ("email_addresses" in document_data or "phone_numbers" in document_data):
            return "contact"
        
        # Check for file-specific fields
        if "name" in document_data and "file_type" in document_data:
            return "file"
        
        # Default to email if we can't determine
        logger.warning("Could not determine document type, defaulting to email")
        return "email"
    
    def _map_fields(self, source: Dict[str, Any], target: Dict[str, Any], mappings: Dict[str, str]) -> Dict[str, Any]:
        """Map fields from source to target using the provided mappings"""
        for source_field, target_field in mappings.items():
            if source_field in source and source[source_field] is not None:
                target[target_field] = source[source_field]
        
        return target
    
    def _generate_search_text(self, vespa_doc: Dict[str, Any], doc_type: str) -> str:
        """Generate searchable text content for the document"""
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
                if isinstance(vespa_doc["recipients"], list):
                    search_parts.append(f"To: {', '.join(vespa_doc['recipients'])}")
                else:
                    search_parts.append(f"To: {vespa_doc['recipients']}")
        
        elif doc_type == "calendar":
            if vespa_doc.get("location"):
                search_parts.append(f"Location: {vespa_doc['location']}")
            if vespa_doc.get("attendees"):
                if isinstance(vespa_doc["attendees"], list):
                    search_parts.append(f"Attendees: {', '.join(vespa_doc['attendees'])}")
                else:
                    search_parts.append(f"Attendees: {vespa_doc['attendees']}")
        
        elif doc_type == "contact":
            if vespa_doc.get("company"):
                search_parts.append(f"Company: {vespa_doc['company']}")
            if vespa_doc.get("job_title"):
                search_parts.append(f"Job: {vespa_doc['job_title']}")
        
        # Join all parts with spaces
        return " ".join(search_parts)
    
    def _extract_metadata(self, document_data: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
        """Extract metadata from the document"""
        metadata = {}
        
        # Common metadata fields
        common_fields = ["created_at", "updated_at", "provider", "source_type"]
        for field in common_fields:
            if field in document_data and document_data[field] is not None:
                metadata[field] = document_data[field]
        
        # Type-specific metadata
        if doc_type == "email":
            metadata.update({
                "has_attachments": document_data.get("has_attachments", False),
                "is_read": document_data.get("is_read", False),
                "is_important": document_data.get("is_important", False),
                "labels": document_data.get("labels", [])
            })
        
        elif doc_type == "calendar":
            metadata.update({
                "is_all_day": document_data.get("is_all_day", False),
                "is_recurring": document_data.get("is_recurring", False),
                "status": document_data.get("status", "busy"),
                "reminder_minutes": document_data.get("reminder_minutes", 15)
            })
        
        elif doc_type == "contact":
            metadata.update({
                "is_favorite": document_data.get("is_favorite", False),
                "categories": document_data.get("categories", []),
                "notes": document_data.get("notes", "")
            })
        
        elif doc_type == "file":
            metadata.update({
                "size_bytes": document_data.get("size", 0),
                "mime_type": document_data.get("mime_type", ""),
                "checksum": document_data.get("checksum", ""),
                "parent_folder": document_data.get("parent_folder", "")
            })
        
        return metadata
    
    def _validate_vespa_document(self, vespa_doc: Dict[str, Any]) -> None:
        """Validate that the Vespa document has required fields"""
        required_fields = ["user_id", "source_type"]
        missing_fields = [field for field in required_fields if not vespa_doc.get(field)]
        
        if missing_fields:
            raise ValueError(f"Missing required fields for Vespa document: {missing_fields}")
        
        # Ensure timestamps are in the correct format
        timestamp_fields = ["created_at", "updated_at"]
        for field in timestamp_fields:
            if vespa_doc.get(field) and isinstance(vespa_doc[field], str):
                try:
                    # Try to parse ISO format
                    datetime.fromisoformat(vespa_doc[field].replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f"Invalid timestamp format for {field}: {vespa_doc[field]}")
                    # Set to current time if invalid
                    vespa_doc[field] = datetime.now().isoformat()
        
        # Ensure lists are actually lists
        list_fields = ["recipients", "attendees", "labels", "categories"]
        for field in list_fields:
            if field in vespa_doc and not isinstance(vespa_doc[field], list):
                if vespa_doc[field] is not None:
                    vespa_doc[field] = [vespa_doc[field]]
                else:
                    vespa_doc[field] = []
        
        logger.debug(f"Vespa document validation passed for {vespa_doc.get('source_type')} document")
    
    def map_batch(self, documents: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """Map a batch of documents to Vespa format"""
        mapped_documents = []
        
        for doc in documents:
            try:
                mapped_doc = self.map_to_vespa(doc)
                mapped_documents.append(mapped_doc)
            except Exception as e:
                logger.error(f"Error mapping document {doc.get('id', 'unknown')}: {e}")
                # Continue with other documents
                continue
        
        logger.info(f"Successfully mapped {len(mapped_documents)} out of {len(documents)} documents")
        return mapped_documents
