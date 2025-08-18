#!/usr/bin/env python3
"""
Test script for Vespa email ingestion and user isolation
"""

import requests
import json
import time
from typing import Dict, Any

VESPA_URL = "http://localhost:8080"

def create_test_document(user_id: str, doc_id: str, content: str) -> Dict[str, Any]:
    """Create a test document for Vespa"""
    return {
        "put": "id:briefly:briefly_document::" + doc_id,
        "fields": {
            "user_id": user_id,
            "doc_id": doc_id,
            "provider": "test",
            "source_type": "email",
            "title": f"Test Email {doc_id}",
            "content": content,
            "search_text": content,
            "sender": "test@example.com",
            "recipients": ["user@example.com"],
            "thread_id": f"thread_{doc_id}",
            "folder": "inbox",
            "created_at": int(time.time() * 1000),
            "updated_at": int(time.time() * 1000),
            "metadata": {
                "test": "true"
            }
        }
    }

def test_document_ingestion():
    """Test basic document ingestion"""
    print("Testing document ingestion...")
    
    # Test document 1
    doc1 = create_test_document("user1", "doc1", "This is a test email about quarterly planning")
    
    response = requests.post(
        f"{VESPA_URL}/document/v1/briefly/briefly_document/docid/{doc1['put']}",
        json=doc1["fields"]
    )
    
    if response.status_code == 200:
        print("✓ Document 1 ingested successfully")
    else:
        print(f"✗ Failed to ingest document 1: {response.status_code} - {response.text}")
        return False
    
    # Test document 2
    doc2 = create_test_document("user2", "doc2", "This is another test email about budget review")
    
    response = requests.post(
        f"{VESPA_URL}/document/v1/briefly/briefly_document/docid/{doc2['put']}",
        json=doc2["fields"]
    )
    
    if response.status_code == 200:
        print("✓ Document 2 ingested successfully")
    else:
        print(f"✗ Failed to ingest document 2: {response.status_code} - {response.text}")
        return False
    
    return True

def test_user_isolation():
    """Test user isolation by searching for documents"""
    print("\nTesting user isolation...")
    
    # Search for user1 documents
    query1 = {
        "yql": "select * from briefly_document where user_id contains 'user1'",
        "hits": 10
    }
    
    response = requests.post(f"{VESPA_URL}/search/", json=query1)
    
    if response.status_code == 200:
        results = response.json()
        user1_count = results.get("root", {}).get("children", [])
        print(f"✓ User1 search returned {len(user1_count)} documents")
        
        # Verify only user1 documents are returned
        for doc in user1_count:
            if doc.get("fields", {}).get("user_id") != "user1":
                print(f"✗ User isolation failed: found user2 document in user1 results")
                return False
    else:
        print(f"✗ User1 search failed: {response.status_code} - {response.text}")
        return False
    
    # Search for user2 documents
    query2 = {
        "yql": "select * from briefly_document where user_id contains 'user2'",
        "hits": 10
    }
    
    response = requests.post(f"{VESPA_URL}/search/", json=query2)
    
    if response.status_code == 200:
        results = response.json()
        user2_count = results.get("root", {}).get("children", [])
        print(f"✓ User2 search returned {len(user2_count)} documents")
        
        # Verify only user2 documents are returned
        for doc in user2_count:
            if doc.get("fields", {}).get("user_id") != "user2":
                print(f"✗ User isolation failed: found user1 document in user2 results")
                return False
    else:
        print(f"✗ User2 search failed: {response.status_code} - {response.text}")
        return False
    
    return True

def test_search_functionality():
    """Test basic search functionality"""
    print("\nTesting search functionality...")
    
    # Test content search
    query = {
        "yql": "select * from briefly_document where search_text contains 'quarterly planning'",
        "hits": 10
    }
    
    response = requests.post(f"{VESPA_URL}/search/", json=query)
    
    if response.status_code == 200:
        results = response.json()
        hits = results.get("root", {}).get("children", [])
        print(f"✓ Content search returned {len(hits)} results")
        
        if len(hits) > 0:
            print("✓ Content search working correctly")
        else:
            print("✗ Content search returned no results")
            return False
    else:
        print(f"✗ Content search failed: {response.status_code} - {response.text}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("Starting Vespa ingestion and isolation tests...")
    
    # Wait for Vespa to be ready
    print("Waiting for Vespa to be ready...")
    time.sleep(5)
    
    # Test document ingestion
    if not test_document_ingestion():
        print("Document ingestion test failed")
        return
    
    # Wait for documents to be indexed
    print("Waiting for documents to be indexed...")
    time.sleep(5)
    
    # Test user isolation
    if not test_user_isolation():
        print("User isolation test failed")
        return
    
    # Test search functionality
    if not test_search_functionality():
        print("Search functionality test failed")
        return
    
    print("\n🎉 All tests passed! Vespa is working correctly.")

if __name__ == "__main__":
    main()
