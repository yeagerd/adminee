#!/usr/bin/env python3
"""
Comprehensive Vespa integration test runner.
This script tests the complete Vespa document lifecycle and catches the issues we discovered.
"""

import asyncio
import json
import sys
import time
from typing import Dict, List, Any
import requests


class VespaIntegrationTester:
    """Test Vespa integration end-to-end."""
    
    def __init__(self, vespa_endpoint: str = "http://localhost:8080"):
        self.vespa_endpoint = vespa_endpoint
        self.test_results = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def test_vespa_health(self) -> bool:
        """Test if Vespa is healthy and responding."""
        try:
            response = requests.get(f"{self.vespa_endpoint}/")
            if response.status_code == 200:
                self.log("✅ Vespa is healthy and responding")
                return True
            else:
                self.log(f"❌ Vespa health check failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Vespa health check error: {e}", "ERROR")
            return False
    
    def test_search_functionality(self) -> Dict[str, Any]:
        """Test basic search functionality."""
        self.log("🔍 Testing search functionality...")
        
        try:
            # Test search for the user we know has data using streaming mode
            search_query = {
                "yql": "select * from briefly_document where true",
                "hits": 10,
                "ranking": "hybrid",
                "streaming.groupname": "trybriefly@outlook.com"  # This ensures user isolation
            }
            
            response = requests.post(f"{self.vespa_endpoint}/search/", json=search_query)
            
            if response.status_code == 200:
                result = response.json()
                children = result.get("root", {}).get("children", [])
                
                self.log(f"✅ Search successful, found {len(children)} documents")
                
                # Analyze document structure
                if children:
                    first_doc = children[0]
                    self.analyze_document_structure(first_doc)
                
                return {
                    "status": "success",
                    "document_count": len(children),
                    "documents": children
                }
            else:
                self.log(f"❌ Search failed: {response.status_code}", "ERROR")
                return {"status": "error", "code": response.status_code}
                
        except Exception as e:
            self.log(f"❌ Search test error: {e}", "ERROR")
            return {"status": "error", "message": str(e)}
    
    def analyze_document_structure(self, document: Dict[str, Any]):
        """Analyze document structure for potential issues."""
        self.log("📋 Analyzing document structure...")
        
        # Check for ID corruption
        vespa_id = document.get("id", "")
        fields = document.get("fields", {})
        doc_id = fields.get("doc_id", "")
        
        # Test 1: ID duplication detection
        if vespa_id.count("id:briefly:briefly_document::") > 1:
            self.log(f"🚨 ID CORRUPTION DETECTED: {vespa_id}", "ERROR")
            self.test_results.append({
                "test": "id_corruption_detection",
                "status": "FAILED",
                "details": f"Vespa ID has duplication: {vespa_id}"
            })
        else:
            self.log("✅ Vespa ID format is correct")
            self.test_results.append({
                "test": "id_corruption_detection",
                "status": "PASSED",
                "details": "No ID corruption detected"
            })
        
        # Test 2: doc_id field corruption
        if doc_id.startswith("id:briefly:briefly_document::"):
            self.log(f"🚨 DOC_ID CORRUPTION DETECTED: {doc_id}", "ERROR")
            self.test_results.append({
                "test": "doc_id_corruption_detection",
                "status": "FAILED",
                "details": f"doc_id field is corrupted: {doc_id}"
            })
        else:
            self.log("✅ doc_id field is correct")
            self.test_results.append({
                "test": "doc_id_corruption_detection",
                "status": "PASSED",
                "details": "doc_id field format is correct"
            })
        
        # Test 3: Field consistency
        # In streaming mode, user_id is automatically extracted from document ID, so we don't need it as a field
        required_fields = ["doc_id", "title", "content", "search_text"]
        missing_fields = [field for field in required_fields if field not in fields]
        
        if missing_fields:
            self.log(f"🚨 Missing required fields: {missing_fields}", "ERROR")
            self.test_results.append({
                "test": "field_completeness",
                "status": "FAILED",
                "details": f"Missing fields: {missing_fields}"
            })
        else:
            self.log("✅ All required fields are present")
            self.test_results.append({
                "test": "field_completeness",
                "status": "PASSED",
                "details": "All required fields present"
            })
        
        # Test 3.5: Verify streaming mode ID format
        vespa_id = document.get("id", "")
        if "g=" in vespa_id and vespa_id.count("id:briefly:briefly_document:g=") == 1:
            self.log("✅ Streaming mode ID format is correct")
            self.test_results.append({
                "test": "streaming_id_format",
                "status": "PASSED",
                "details": "Document ID follows streaming mode format"
            })
        else:
            self.log("🚨 Streaming mode ID format is incorrect", "ERROR")
            self.test_results.append({
                "test": "streaming_id_format",
                "status": "FAILED",
                "details": f"Document ID format incorrect: {vespa_id}"
            })
    
    def test_document_deletion(self, document: Dict[str, Any]) -> bool:
        """Test document deletion functionality."""
        self.log("🗑️ Testing document deletion...")
        
        try:
            vespa_id = document.get("id", "")
            if not vespa_id:
                self.log("❌ No document ID found for deletion test", "ERROR")
                return False
            
            # Extract the doc_id for deletion
            fields = document.get("fields", {})
            doc_id = fields.get("doc_id", "")
            
            if not doc_id:
                self.log("❌ No doc_id field found for deletion test", "ERROR")
                return False
            
            # Construct deletion URL
            delete_url = f"{self.vespa_endpoint}/document/v1/briefly/briefly_document/docid/{vespa_id}"
            
            self.log(f"🗑️ Attempting to delete document: {vespa_id}")
            response = requests.delete(delete_url)
            
            if response.status_code == 200:
                result = response.json()
                self.log(f"✅ Document deletion successful: {result}")
                
                # Check if deletion response indicates success
                if "pathId" in result and "id" in result:
                    self.log("✅ Deletion response format is correct")
                    self.test_results.append({
                        "test": "document_deletion",
                        "status": "PASSED",
                        "details": "Document deleted successfully"
                    })
                    return True
                else:
                    self.log("⚠️ Deletion response format is unexpected", "WARNING")
                    self.test_results.append({
                        "test": "document_deletion",
                        "status": "WARNING",
                        "details": "Unexpected deletion response format"
                    })
                    return True
            else:
                self.log(f"❌ Document deletion failed: {response.status_code}", "ERROR")
                error_text = response.text
                self.log(f"❌ Error details: {error_text}", "ERROR")
                
                self.test_results.append({
                    "test": "document_deletion",
                    "status": "FAILED",
                    "details": f"Deletion failed with status {response.status_code}: {error_text}"
                })
                return False
                
        except Exception as e:
            self.log(f"❌ Deletion test error: {e}", "ERROR")
            self.test_results.append({
                "test": "document_deletion",
                "status": "ERROR",
                "message": str(e)
            })
            return False
    
    def test_data_consistency(self) -> Dict[str, Any]:
        """Test data consistency across different operations."""
        self.log("🔄 Testing data consistency...")
        
        try:
            # Test 1: Count documents for a specific user using streaming mode
            user_id = "trybriefly@outlook.com"
            count_query = {
                "yql": "select * from briefly_document where true",
                "hits": 0,  # Just get count
                "ranking": "hybrid",
                "streaming.groupname": user_id  # This ensures user isolation
            }
            
            response = requests.post(f"{self.vespa_endpoint}/search/", json=count_query)
            
            if response.status_code == 200:
                result = response.json()
                total_found = result.get("root", {}).get("fields", {}).get("totalCount", 0)
                
                self.log(f"📊 Found {total_found} documents for user {user_id}")
                
                # Test 2: Get actual documents using streaming mode
                search_query = {
                    "yql": "select * from briefly_document where true",
                    "hits": 400,
                    "ranking": "hybrid",
                    "streaming.groupname": user_id  # This ensures user isolation
                }
                
                response = requests.post(f"{self.vespa_endpoint}/search/", json=search_query)
                
                if response.status_code == 200:
                    result = response.json()
                    children = result.get("root", {}).get("children", [])
                    
                    self.log(f"📋 Retrieved {len(children)} documents")
                    
                    # Check consistency
                    if total_found == len(children):
                        self.log("✅ Document count consistency: PASSED")
                        self.test_results.append({
                            "test": "document_count_consistency",
                            "status": "PASSED",
                            "details": f"Count matches: {total_found} = {len(children)}"
                        })
                    else:
                        self.log(f"🚨 Document count inconsistency: {total_found} != {len(children)}", "ERROR")
                        self.test_results.append({
                            "test": "document_count_consistency",
                            "status": "FAILED",
                            "details": f"Count mismatch: {total_found} != {len(children)}"
                        })
                    
                    return {
                        "status": "success",
                        "total_count": total_found,
                        "retrieved_count": len(children),
                        "consistent": total_found == len(children)
                    }
                else:
                    self.log(f"❌ Document retrieval failed: {response.status_code}", "ERROR")
                    return {"status": "error", "code": response.status_code}
            else:
                self.log(f"❌ Count query failed: {response.status_code}", "ERROR")
                return {"status": "error", "code": response.status_code}
                
        except Exception as e:
            self.log(f"❌ Consistency test error: {e}", "ERROR")
            return {"status": "error", "message": str(e)}
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests."""
        self.log("🚀 Starting Vespa integration tests...")
        
        # Test 1: Health check
        if not self.test_vespa_health():
            self.log("❌ Vespa health check failed, aborting tests", "ERROR")
            return {"status": "failed", "reason": "Vespa not healthy"}
        
        # Test 2: Search functionality
        search_result = self.test_search_functionality()
        
        # Test 3: Document deletion (if documents exist)
        if search_result.get("status") == "success" and search_result.get("documents"):
            first_doc = search_result["documents"][0]
            self.test_document_deletion(first_doc)
        
        # Test 4: Data consistency
        consistency_result = self.test_data_consistency()
        
        # Test 5: User isolation validation
        isolation_result = self.test_user_isolation()
        
        # Generate summary
        passed_tests = [r for r in self.test_results if r["status"] == "PASSED"]
        failed_tests = [r for r in self.test_results if r["status"] == "FAILED"]
        critical_failures = [r for r in self.test_results if r["status"] == "CRITICAL_FAILURE"]
        warning_tests = [r for r in self.test_results if r["status"] == "WARNING"]
        
        summary = {
            "status": "completed",
            "total_tests": len(self.test_results),
            "passed": len(passed_tests),
            "failed": len(failed_tests),
            "critical_failures": len(critical_failures),
            "warnings": len(warning_tests),
            "results": self.test_results
        }
        
        self.log(f"📊 Test Summary: {summary['passed']}/{summary['total_tests']} tests passed")
        
        if critical_failures:
            self.log("🚨🚨🚨 CRITICAL FAILURES (Security Issues):", "ERROR")
            for test in critical_failures:
                self.log(f"  - {test['test']}: {test.get('details', 'No details')}", "ERROR")
                if 'security_implication' in test:
                    self.log(f"    SECURITY IMPLICATION: {test['security_implication']}", "ERROR")
        
        if failed_tests:
            self.log("🚨 Failed tests:", "ERROR")
            for test in failed_tests:
                self.log(f"  - {test['test']}: {test.get('details', test.get('message', 'No details'))}", "ERROR")
        
        if warning_tests:
            self.log("⚠️ Warning tests:", "WARNING")
            for test in warning_tests:
                self.log(f"  - {test['test']}: {test.get('details', 'No details')}", "WARNING")
        
        return summary
    
    def test_user_isolation(self) -> Dict[str, Any]:
        """Test that user isolation is working correctly."""
        self.log("🔒 Testing user isolation...")
        
        try:
            # Test 1: Verify that documents have user_id field
            user_id = "trybriefly@outlook.com"
            search_query = {
                "yql": f"select * from briefly_document where user_id contains \"{user_id}\"",
                "hits": 5,
                "ranking": "hybrid",
                "streaming.groupname": user_id  # Required for streaming mode
            }
            
            response = requests.post(f"{self.vespa_endpoint}/search/", json=search_query)
            
            if response.status_code == 200:
                result = response.json()
                children = result.get("root", {}).get("children", [])
                
                if children:
                    # Check first document for streaming mode ID format
                    first_doc = children[0]
                    vespa_id = first_doc.get("id", "")
                    
                    # In streaming mode, user_id is extracted from the document ID
                    if "g=" in vespa_id and vespa_id.count("id:briefly:briefly_document:g=") == 1:
                        # Extract user_id from the streaming ID format
                        try:
                            # Format: id:briefly:briefly_document:g={user_id}:{doc_id}
                            parts = vespa_id.split(":g=")
                            if len(parts) == 2:
                                user_part = parts[1].split(":")[0]
                                if user_part == user_id:
                                    self.log("✅ Streaming mode user isolation working correctly")
                                    self.test_results.append({
                                        "test": "user_isolation_field_presence",
                                        "status": "PASSED",
                                        "details": "User isolation working through streaming mode ID format"
                                    })
                                else:
                                    self.log(f"🚨 user_id mismatch in streaming ID: expected {user_id}, got {user_part}", "ERROR")
                                    self.test_results.append({
                                        "test": "user_isolation_field_presence",
                                        "status": "FAILED",
                                        "details": f"user_id mismatch in streaming ID: expected {user_id}, got {user_part}"
                                    })
                            else:
                                self.log("🚨 Invalid streaming ID format", "ERROR")
                                self.test_results.append({
                                    "test": "user_isolation_field_presence",
                                    "status": "FAILED",
                                    "details": f"Invalid streaming ID format: {vespa_id}"
                                })
                        except Exception as e:
                            self.log(f"🚨 Error parsing streaming ID: {e}", "ERROR")
                            self.test_results.append({
                                "test": "user_isolation_field_presence",
                                "status": "FAILED",
                                "details": f"Error parsing streaming ID: {e}"
                            })
                    else:
                        self.log("🚨🚨🚨 CRITICAL: Document ID is not in streaming mode format!", "ERROR")
                        self.log("🚨 This breaks user isolation and is a security vulnerability!", "ERROR")
                        
                        self.test_results.append({
                            "test": "user_isolation_field_presence",
                            "status": "CRITICAL_FAILURE",
                            "details": "Document ID is not in streaming mode format",
                            "security_implication": "User isolation broken - documents can be accessed by any user"
                        })
                        
                        return {"status": "critical_failure", "reason": "Invalid streaming ID format"}
                    
                    # Test 2: Verify that searching for different user returns no results
                    other_user = "other@example.com"
                    other_search_query = {
                        "yql": "select * from briefly_document where true",
                        "hits": 5,
                        "ranking": "hybrid",
                        "streaming.groupname": other_user  # This should return no results for other user
                    }
                    
                    other_response = requests.post(f"{self.vespa_endpoint}/search/", json=other_search_query)
                    
                    if other_response.status_code == 200:
                        other_result = other_response.json()
                        other_children = other_result.get("root", {}).get("children", [])
                        
                        if len(other_children) == 0:
                            self.log("✅ User isolation working: other user search returns no results")
                            self.test_results.append({
                                "test": "user_isolation_search",
                                "status": "PASSED",
                                "details": "Other user search correctly returns no results"
                            })
                        else:
                            self.log(f"🚨 User isolation broken: other user search returned {len(other_children)} results", "ERROR")
                            self.test_results.append({
                                "test": "user_isolation_search",
                                "status": "FAILED",
                                "details": f"Other user search returned {len(other_children)} results when it should return 0"
                            })
                    
                    return {"status": "success", "user_isolation_working": True}
                else:
                    self.log("⚠️ No documents found to test user isolation", "WARNING")
                    return {"status": "warning", "reason": "No documents to test"}
            else:
                self.log(f"❌ User isolation test failed: {response.status_code}", "ERROR")
                return {"status": "error", "code": response.status_code}
                
        except Exception as e:
            self.log(f"❌ User isolation test error: {e}", "ERROR")
            return {"status": "error", "message": str(e)}
    
    def save_results(self, filename: str = "vespa_integration_test_results.json"):
        """Save test results to a file."""
        try:
            with open(filename, 'w') as f:
                json.dump(self.test_results, f, indent=2)
            self.log(f"💾 Test results saved to {filename}")
        except Exception as e:
            self.log(f"❌ Failed to save results: {e}", "ERROR")


async def main():
    """Main test runner."""
    tester = VespaIntegrationTester()
    
    # Run tests
    results = tester.run_all_tests()
    
    # Save results
    tester.save_results()
    
    # Exit with appropriate code
    if results.get("failed", 0) > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
