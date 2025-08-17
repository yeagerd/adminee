# Vespa Integration Test Suite

This test suite is designed to catch the Vespa integration issues we discovered during manual testing, including:

## 🚨 **Issues This Test Suite Catches:**

### 1. **Document ID Corruption**
- **Problem**: Documents indexed with duplicated IDs like `id:briefly:briefly_document::id:briefly:briefly_document::ms_9`
- **Test**: `test_corrupted_id_handling()` in `test_document_indexing.py`
- **Detection**: Checks for ID duplication patterns

### 2. **Field Mapping Inconsistencies**
- **Problem**: Confusion between `doc_id`, `id`, and `documentid` fields
- **Test**: `test_document_id_field_extraction()` in `test_search_consistency.py`
- **Detection**: Validates field structure and content

### 3. **Deletion API Failures**
- **Problem**: Document deletion operations fail even with correct IDs
- **Test**: `test_deletion_error_handling()` in `test_vespa_client_integration.py`
- **Detection**: Mocks deletion failures and validates error handling

### 4. **Data Consistency Issues**
- **Problem**: Search results don't match expected document counts
- **Test**: `test_search_result_consistency()` in `test_search_consistency.py`
- **Detection**: Compares count queries with actual result sets

## 🧪 **Test Files:**

### `test_vespa_client_integration.py`
- **Purpose**: Test complete document lifecycle (index → search → delete → verify)
- **Key Tests**:
  - Document ID generation consistency
  - Document lifecycle consistency
  - Batch operations ID consistency
  - Deletion error handling

### `test_document_indexing.py`
- **Purpose**: Test document indexing operations and ID handling
- **Key Tests**:
  - Content normalization preserves doc_id
  - Indexing preserves original doc_id without corruption
  - Field mapping consistency across email types
  - Vespa ID generation consistency

### `test_search_consistency.py`
- **Purpose**: Test search consistency and result validation
- **Key Tests**:
  - Corrupted ID detection
  - Search result count validation
  - Field type validation
  - Malformed response handling

## 🚀 **Running the Tests:**

### Unit Tests (Mocked)
```bash
# Run all Vespa loader tests
cd services/vespa_loader
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_document_indexing.py -v

# Run specific test
python -m pytest tests/test_document_indexing.py::TestDocumentIndexing::test_indexing_preserves_original_doc_id -v
```

### Integration Tests (Real Vespa)
```bash
# Run comprehensive integration tests
./scripts/test_vespa_integration.py

# This will:
# 1. Check Vespa health
# 2. Test search functionality
# 3. Analyze document structure for corruption
# 4. Test document deletion
# 5. Validate data consistency
# 6. Save results to JSON file
```

## 🔍 **What the Integration Tests Check:**

### 1. **ID Corruption Detection**
```python
# Checks for duplicated IDs like:
# id:briefly:briefly_document::id:briefly:briefly_document::ms_9
if vespa_id.count("id:briefly:briefly_document::") > 1:
    # Corruption detected!
```

### 2. **Field Corruption Detection**
```python
# Checks if doc_id field contains Vespa ID format
if doc_id.startswith("id:briefly:briefly_document::"):
    # Field corruption detected!
```

### 3. **Document Structure Validation**
```python
# Ensures all required fields are present
required_fields = ["user_id", "doc_id", "title", "content", "search_text"]
missing_fields = [field for field in required_fields if field not in fields]
```

### 4. **Data Consistency Validation**
```python
# Compares count query results with actual document retrieval
if total_found == len(children):
    # Consistency: PASSED
else:
    # Inconsistency: FAILED
```

## 📊 **Test Results:**

The integration test runner provides detailed results:

```json
{
  "status": "completed",
  "total_tests": 4,
  "passed": 2,
  "failed": 1,
  "warnings": 1,
  "results": [
    {
      "test": "id_corruption_detection",
      "status": "FAILED",
      "details": "Vespa ID has duplication: id:briefly:briefly_document::id:briefly:briefly_document::ms_9"
    }
  ]
}
```

## 🎯 **How This Improves Our Test Loop:**

### **Before (Manual Testing)**
1. Run `--clear-data` manually
2. Check if it "worked" by eye
3. Run search script manually
4. Discover issues through trial and error
5. Debug manually with print statements

### **After (Automated Testing)**
1. Run `./scripts/test_vespa_integration.py`
2. Get immediate feedback on all issues
3. See exactly which tests failed and why
4. Have reproducible test cases
5. Catch regressions automatically

## 🔧 **Adding New Tests:**

When you discover new issues, add tests to catch them:

```python
def test_new_issue_detection(self, vespa_client):
    """Test that catches the new issue we discovered."""
    # Test setup
    # ... 
    
    # This assertion should fail if the issue occurs
    assert not has_the_problem_we_discovered
    
    # Add to test_results for reporting
    self.test_results.append({
        "test": "new_issue_detection",
        "status": "PASSED",
        "details": "New issue not detected"
    })
```

## 🚀 **Continuous Integration:**

These tests can be integrated into CI/CD pipelines to catch issues before they reach production:

```yaml
# Example GitHub Actions step
- name: Test Vespa Integration
  run: |
    ./scripts/test_vespa_integration.py
  env:
    VESPA_ENDPOINT: ${{ secrets.VESPA_ENDPOINT }}
```

This test suite transforms our reactive debugging approach into a proactive testing strategy that catches issues early and provides clear, actionable feedback.
