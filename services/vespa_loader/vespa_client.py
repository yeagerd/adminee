#!/usr/bin/env python3
"""
Vespa HTTP API client for the loader service
"""

import aiohttp
import logging
from typing import Dict, Any, Optional, List
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class VespaClient:
    """Client for interacting with Vespa HTTP API"""
    
    def __init__(self, vespa_endpoint: str):
        self.vespa_endpoint = vespa_endpoint.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def start(self):
        """Start the client and create HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        logger.info("Vespa client started")
    
    async def close(self):
        """Close the client and HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
        logger.info("Vespa client closed")
    
    async def test_connection(self) -> bool:
        """Test connection to Vespa"""
        try:
            if not self.session:
                await self.start()
            
            async with self.session.get(f"{self.vespa_endpoint}/application/v2/status") as response:
                if response.status == 200:
                    logger.info("Vespa connection test successful")
                    return True
                else:
                    logger.error(f"Vespa connection test failed with status {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Vespa connection test failed: {e}")
            return False
    
    async def index_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Index a document into Vespa"""
        if not self.session:
            await self.start()
        
        try:
            # Prepare document for Vespa
            vespa_doc = self._prepare_document_for_indexing(document)
            
            # Generate document ID
            doc_id = self._generate_document_id(document)
            
            # Index document
            url = f"{self.vespa_endpoint}/document/v1/briefly/briefly_document/docid/{doc_id}"
            
            async with self.session.post(url, json=vespa_doc) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Successfully indexed document {doc_id}")
                    return {
                        "id": doc_id,
                        "status": "success",
                        "result": result
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to index document {doc_id}: {response.status} - {error_text}")
                    raise Exception(f"Indexing failed: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"Error indexing document: {e}")
            raise
    
    async def delete_document(self, user_id: str, doc_id: str) -> Dict[str, Any]:
        """Delete a document from Vespa"""
        if not self.session:
            await self.start()
        
        try:
            # Generate full document ID
            full_doc_id = f"id:briefly:briefly_document::{doc_id}"
            
            url = f"{self.vespa_endpoint}/document/v1/briefly/briefly_document/docid/{full_doc_id}"
            
            async with self.session.delete(url) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Successfully deleted document {doc_id}")
                    return {
                        "id": doc_id,
                        "status": "success",
                        "result": result
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to delete document {doc_id}: {response.status} - {error_text}")
                    raise Exception(f"Deletion failed: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise
    
    async def get_document(self, user_id: str, doc_id: str) -> Dict[str, Any]:
        """Retrieve a document from Vespa"""
        if not self.session:
            await self.start()
        
        try:
            # Generate full document ID
            full_doc_id = f"id:briefly:briefly_document::{doc_id}"
            
            url = f"{self.vespa_endpoint}/document/v1/briefly/briefly_document/docid/{full_doc_id}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Successfully retrieved document {doc_id}")
                    return result
                elif response.status == 404:
                    logger.warning(f"Document {doc_id} not found")
                    return {"error": "Document not found"}
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to retrieve document {doc_id}: {response.status} - {error_text}")
                    raise Exception(f"Retrieval failed: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"Error retrieving document: {e}")
            raise
    
    async def search_documents(self, query: str, user_id: str, limit: int = 10) -> Dict[str, Any]:
        """Search for documents in Vespa"""
        if not self.session:
            await self.start()
        
        try:
            # Build search query
            search_query = {
                "yql": f'select * from briefly_document where user_id contains "{user_id}" and (search_text contains "{query}" or title contains "{query}")',
                "hits": limit,
                "ranking": "hybrid"
            }
            
            url = f"{self.vespa_endpoint}/search/"
            
            async with self.session.post(url, json=search_query) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Search query '{query}' returned {len(result.get('root', {}).get('children', []))} results")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"Search query failed: {response.status} - {error_text}")
                    raise Exception(f"Search failed: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            raise
    
    async def batch_index_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Index multiple documents in batch"""
        if not self.session:
            await self.start()
        
        try:
            results = []
            
            # Process documents in parallel
            import asyncio
            tasks = [self.index_document(doc) for doc in documents]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    results.append({
                        "index": i,
                        "status": "error",
                        "error": str(result)
                    })
                else:
                    results.append({
                        "index": i,
                        "status": "success",
                        "result": result
                    })
            
            return {
                "status": "completed",
                "total_documents": len(documents),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error in batch indexing: {e}")
            raise
    
    def _prepare_document_for_indexing(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare document for Vespa indexing"""
        # Ensure required fields are present
        required_fields = ["user_id", "doc_id", "provider", "source_type"]
        for field in required_fields:
            if field not in document:
                raise ValueError(f"Missing required field: {field}")
        
        # Convert timestamps to milliseconds if they're datetime objects
        if "created_at" in document and isinstance(document["created_at"], datetime):
            document["created_at"] = int(document["created_at"].timestamp() * 1000)
        
        if "updated_at" in document and isinstance(document["updated_at"], datetime):
            document["updated_at"] = int(document["updated_at"].timestamp() * 1000)
        
        # Ensure recipients is a list
        if "recipients" in document and not isinstance(document["recipients"], list):
            document["recipients"] = [document["recipients"]]
        
        # Ensure metadata is a dict
        if "metadata" not in document:
            document["metadata"] = {}
        
        return document
    
    def _generate_document_id(self, document: Dict[str, Any]) -> str:
        """Generate a unique document ID for Vespa"""
        user_id = document.get("user_id", "unknown")
        doc_id = document.get("doc_id", "unknown")
        provider = document.get("provider", "unknown")
        
        # Create a unique ID that includes user and provider for isolation
        unique_id = f"{user_id}_{provider}_{doc_id}"
        
        # Remove any characters that might cause issues in URLs
        unique_id = unique_id.replace(" ", "_").replace("/", "_").replace("\\", "_")
        
        return unique_id
