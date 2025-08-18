#!/usr/bin/env python3
"""
Vespa HTTP API client for the loader service
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp

from services.common.logging_config import get_logger
from services.common.telemetry import get_tracer

logger = get_logger(__name__)
tracer = get_tracer(__name__)


class VespaClient:
    """Client for interacting with Vespa HTTP API"""

    def __init__(self, vespa_endpoint: str) -> None:
        self.vespa_endpoint = vespa_endpoint.rstrip("/")
        self.session: Optional[aiohttp.ClientSession] = None

    async def start(self) -> None:
        """Start the client and create HTTP session"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self.session = aiohttp.ClientSession(timeout=timeout)
        logger.info("Vespa client started")

    async def close(self) -> None:
        """Close the client and HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
        logger.info("Vespa client closed")

    async def test_connection(self) -> bool:
        """Test connection to Vespa"""
        with tracer.start_as_current_span("vespa.test_connection") as span:
            span.set_attribute("vespa.endpoint", self.vespa_endpoint)

            try:
                if not self.session:
                    await self.start()

                if self.session:
                    async with self.session.get(f"{self.vespa_endpoint}/") as response:
                        span.set_attribute("vespa.response.status", response.status)

                        if response.status == 200:
                            logger.info("Vespa connection test successful")
                            span.set_attribute("vespa.connection.success", True)
                            return True
                        else:
                            logger.error(
                                f"Vespa connection test failed with status {response.status}"
                            )
                            span.set_attribute("vespa.connection.success", False)
                            span.set_attribute("vespa.error.status", response.status)
                            return False
                return False
            except Exception as e:
                logger.error(f"Vespa connection test failed: {e}")
                span.set_attribute("vespa.connection.success", False)
                span.set_attribute("vespa.error.message", str(e))
                span.record_exception(e)
                return False

    async def index_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Index a document into Vespa"""
        with tracer.start_as_current_span("vespa.index_document") as span:
            span.set_attribute(
                "vespa.document.type", document.get("source_type", "unknown")
            )
            span.set_attribute(
                "vespa.document.user_id", document.get("user_id", "unknown")
            )

            if not self.session:
                await self.start()

            try:
                # Prepare document for Vespa
                vespa_doc: Dict[str, Any] = self._prepare_document_for_indexing(
                    document
                )

                # Generate document ID
                doc_id = self._generate_document_id(document)
                # Use streaming mode ID format: id:briefly:briefly_document:g={user_id}:{doc_id}
                user_id = document.get("user_id", "unknown")
                full_doc_id = f"id:briefly:briefly_document:g={user_id}:{doc_id}"
                span.set_attribute("vespa.document.id", full_doc_id)

                # Index document using streaming mode URL format
                # Correct format: /document/v1/{namespace}/{documenttype}/group/{groupname}/{docid}
                url = f"{self.vespa_endpoint}/document/v1/briefly/briefly_document/group/{user_id}/{doc_id}"
                span.set_attribute("vespa.request.url", url)

                if self.session:
                    async with self.session.post(url, json=vespa_doc) as response:
                        span.set_attribute("vespa.response.status", response.status)

                        if response.status == 200:
                            result = await response.json()
                            logger.info(f"Successfully indexed document {doc_id}")
                            span.set_attribute("vespa.indexing.success", True)
                            return {
                                "id": full_doc_id,
                                "status": "success",
                                "result": result,
                            }
                        else:
                            error_text = await response.text()
                            logger.error(
                                f"Failed to index document {doc_id}: {response.status} - {error_text}"
                            )
                            span.set_attribute("vespa.indexing.success", False)
                            span.set_attribute("vespa.error.status", response.status)
                            span.set_attribute("vespa.error.message", error_text)
                            raise Exception(f"HTTP {response.status}: {error_text}")
                else:
                    raise Exception("No session available")

            except Exception as e:
                logger.error(
                    f"Error indexing document {document.get('id', 'unknown')}: {e}"
                )
                span.set_attribute("vespa.indexing.success", False)
                span.record_exception(e)
                raise

    async def get_document(self, doc_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a document from Vespa"""
        with tracer.start_as_current_span("vespa.get_document") as span:
            span.set_attribute("vespa.document.id", doc_id)
            span.set_attribute("vespa.document.user_id", user_id)

            if not self.session:
                await self.start()

            try:
                # Use streaming mode URL format
                url = f"{self.vespa_endpoint}/document/v1/briefly/briefly_document/group/{user_id}/{doc_id}"
                span.set_attribute("vespa.request.url", url)

                if self.session:
                    async with self.session.get(url) as response:
                        span.set_attribute("vespa.response.status", response.status)

                        if response.status == 200:
                            result = await response.json()
                            logger.info(f"Successfully retrieved document {doc_id}")
                            span.set_attribute("vespa.retrieval.success", True)
                            return result
                        elif response.status == 404:
                            logger.info(f"Document {doc_id} not found")
                            span.set_attribute("vespa.retrieval.success", False)
                            span.set_attribute("vespa.error.status", 404)
                            return None
                        else:
                            error_text = await response.text()
                            logger.error(
                                f"Failed to get document {doc_id}: {response.status} - {error_text}"
                            )
                            span.set_attribute("vespa.retrieval.success", False)
                            span.set_attribute("vespa.error.status", response.status)
                            span.set_attribute("vespa.error.message", error_text)
                            raise Exception(f"HTTP {response.status}: {error_text}")
                else:
                    raise Exception("No session available")

            except Exception as e:
                logger.error(f"Error getting document {doc_id}: {e}")
                span.set_attribute("vespa.retrieval.success", False)
                span.record_exception(e)
                raise

    async def delete_document(self, doc_id: str, user_id: str) -> bool:
        """Delete a document from Vespa"""
        with tracer.start_as_current_span("vespa.delete_document") as span:
            span.set_attribute("vespa.document.id", doc_id)
            span.set_attribute("vespa.document.user_id", user_id)

            if not self.session:
                await self.start()

            try:
                # Use streaming mode URL format
                url = f"{self.vespa_endpoint}/document/v1/briefly/briefly_document/group/{user_id}/{doc_id}"
                span.set_attribute("vespa.request.url", url)

                if self.session:
                    async with self.session.delete(url) as response:
                        span.set_attribute("vespa.response.status", response.status)

                        if response.status == 200:
                            logger.info(f"Successfully deleted document {doc_id}")
                            span.set_attribute("vespa.deletion.success", True)
                            return True
                        else:
                            error_text = await response.text()
                            logger.error(
                                f"Failed to delete document {doc_id}: {response.status} - {error_text}"
                            )
                            span.set_attribute("vespa.deletion.success", False)
                            span.set_attribute("vespa.error.status", response.status)
                            span.set_attribute("vespa.error.message", error_text)
                            raise Exception(f"HTTP {response.status}: {error_text}")
                else:
                    raise Exception("No session available")

            except Exception as e:
                logger.error(f"Error deleting document {doc_id}: {e}")
                span.set_attribute("vespa.deletion.success", False)
                span.record_exception(e)
                raise

    async def search_documents(
        self, query: str, user_id: str, limit: int = 10
    ) -> Dict[str, Any]:
        """Search documents in Vespa"""
        with tracer.start_as_current_span("vespa.search_documents") as span:
            span.set_attribute("vespa.query", query)
            span.set_attribute("vespa.document.user_id", user_id)
            span.set_attribute("vespa.search.limit", limit)

            if not self.session:
                await self.start()

            try:
                # Prepare search query
                search_query = {
                    "yql": f'select * from briefly_document where user_id="{user_id}" and userInput(@query)',
                    "query": query,
                    "hits": limit,
                    "timeout": "5.0s",
                }

                url = f"{self.vespa_endpoint}/search/"
                span.set_attribute("vespa.request.url", url)

                if self.session:
                    async with self.session.post(url, json=search_query) as response:
                        span.set_attribute("vespa.response.status", response.status)

                        if response.status == 200:
                            result = await response.json()
                            logger.info(
                                f"Successfully searched documents for user {user_id}"
                            )
                            span.set_attribute("vespa.search.success", True)
                            return result
                        else:
                            error_text = await response.text()
                            logger.error(
                                f"Failed to search documents: {response.status} - {error_text}"
                            )
                            span.set_attribute("vespa.search.success", False)
                            span.set_attribute("vespa.error.status", response.status)
                            span.set_attribute("vespa.error.message", error_text)
                            raise Exception(f"HTTP {response.status}: {error_text}")
                else:
                    raise Exception("No session available")

            except Exception as e:
                logger.error(f"Error searching documents: {e}")
                span.set_attribute("vespa.search.success", False)
                span.record_exception(e)
                raise

    async def get_document_count(self, user_id: str) -> int:
        """Get the total count of documents for a user"""
        with tracer.start_as_current_span("vespa.get_document_count") as span:
            span.set_attribute("vespa.document.user_id", user_id)

            if not self.session:
                await self.start()

            try:
                # Use streaming search query to get count for the specific user group
                search_query = {
                    "yql": f'select count() from briefly_document where user_id contains "{user_id}"',
                    "timeout": "5.0s",
                    "streaming.groupname": user_id,  # Add streaming group parameter
                }

                url = f"{self.vespa_endpoint}/search/"
                span.set_attribute("vespa.request.url", url)

                if self.session:
                    async with self.session.post(url, json=search_query) as response:
                        span.set_attribute("vespa.response.status", response.status)

                        if response.status == 200:
                            result = await response.json()
                            count = (
                                result.get("root", {})
                                .get("fields", {})
                                .get("count()", 0)
                            )
                            logger.info(f"Document count for user {user_id}: {count}")
                            span.set_attribute("vespa.count.success", True)
                            span.set_attribute("vespa.count.value", count)
                            return count
                        else:
                            error_text = await response.text()
                            logger.error(
                                f"Failed to get document count: {response.status} - {error_text}"
                            )
                            span.set_attribute("vespa.count.success", False)
                            span.set_attribute("vespa.error.status", response.status)
                            span.set_attribute("vespa.error.message", error_text)
                            raise Exception(f"HTTP {response.status}: {error_text}")
                else:
                    raise Exception("No session available")

            except Exception as e:
                logger.error(f"Error getting document count: {e}")
                span.set_attribute("vespa.count.success", False)
                span.record_exception(e)
                raise

    def _prepare_document_for_indexing(
        self, document: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare a document for Vespa indexing"""
        # Helper function to convert ISO datetime to Unix timestamp
        def parse_datetime_to_timestamp(datetime_str: str) -> int:
            """Convert ISO datetime string to Unix timestamp (seconds since epoch)"""
            try:
                from datetime import datetime
                # Parse the ISO datetime string
                dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                # Convert to Unix timestamp (seconds since epoch)
                return int(dt.timestamp())
            except (ValueError, TypeError):
                # If parsing fails, return current timestamp as fallback
                from datetime import datetime, timezone
                return int(datetime.now(timezone.utc).timestamp())
        
        # Helper function to clean metadata for Vespa schema
        def clean_metadata_for_vespa(metadata: Any) -> Dict[str, str]:
            """Clean metadata to ensure it only contains string values for Vespa map<string,string>"""
            if not isinstance(metadata, dict):
                return {}
            
            cleaned = {}
            for key, value in metadata.items():
                if isinstance(key, str) and isinstance(value, str):
                    cleaned[key] = value
                elif isinstance(key, str) and value is not None:
                    # Convert non-string values to strings
                    cleaned[key] = str(value)
            
            return cleaned
        
        # Extract the fields we want to index, mapping to Vespa schema field names
        vespa_doc = {
            "fields": {
                "doc_id": document.get("id"),  # Map 'id' to 'doc_id' for Vespa schema
                "user_id": document.get("user_id"),
                "source_type": document.get("source_type", "unknown"),
                "provider": document.get("provider", "unknown"),
                "title": document.get("subject", ""),  # Map 'subject' to 'title' for Vespa schema
                "content": document.get("body", ""),   # Map 'body' to 'content' for Vespa schema
                "search_text": document.get("body", ""),  # Use body content for search_text
                "sender": document.get("from", ""),    # Map 'from' to 'sender' for Vespa schema
                "recipients": document.get("to", []),  # Map 'to' to 'recipients' for Vespa schema
                "thread_id": document.get("thread_id", ""),
                "folder": document.get("folder", ""),
                "created_at": parse_datetime_to_timestamp(document.get("created_at", "")),
                "updated_at": parse_datetime_to_timestamp(document.get("updated_at", "")),
                "metadata": clean_metadata_for_vespa(document.get("metadata", {})),
                # Remove 'timestamp' as it's not in Vespa schema
            }
        }

        # Add any additional fields that might be present (but avoid duplicates)
        for key, value in document.items():
            if key not in vespa_doc["fields"] and value is not None:
                vespa_doc["fields"][key] = value

        return vespa_doc

    def _generate_document_id(self, document: Dict[str, Any]) -> str:
        """Generate a unique document ID for Vespa"""
        # Use a combination of fields to create a unique ID
        doc_id = document.get("id", "")
        source_type = document.get("source_type", "unknown")
        provider = document.get("provider", "unknown")

        if doc_id:
            return f"{source_type}_{provider}_{doc_id}"
        else:
            # Fallback to timestamp-based ID
            timestamp = int(datetime.now(timezone.utc).timestamp())
            return f"{source_type}_{provider}_{timestamp}"
