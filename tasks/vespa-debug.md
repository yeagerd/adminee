# Vespa Debug & Testing Tasks

## Overview
This document outlines the complete workflow for debugging Vespa issues, managing data, and testing the streaming mode implementation. It covers the critical fixes we've implemented and the remaining work needed.

## Critical Issues Resolved ✅

### 1. Missing `user_id` Field - RESOLVED
- **Problem**: Documents indexed without `user_id` field, breaking user isolation
- **Root Cause**: Vespa was in indexed mode, not streaming mode
- **Fix**: Changed `mode="index"` to `mode="streaming"` in `vespa/services.xml`
- **Result**: `user_id` is now automatically extracted from document IDs

### 2. ID Corruption - RESOLVED
- **Problem**: Document IDs had duplicated format like `id:briefly:briefly_document::id:briefly:briefly_document::...`
- **Root Cause**: ID generation didn't follow streaming mode format
- **Fix**: Updated ID format to `id:briefly:briefly_document:g={user_id}:{doc_id}`
- **Result**: Clean, streaming-compatible document IDs

### 3. Search Query Failures - RESOLVED ✅
- **Problem**: Search queries failed with "Streaming search requires streaming.groupname" errors
- **Root Cause**: Queries didn't include required streaming parameters
- **Fix**: Added `"streaming.groupname": user_id` to all search queries in VespaSearchTool and SemanticSearchTool
- **Result**: User isolation now works through Vespa's streaming mechanism
- **Files Fixed**: `services/chat/agents/llm_tools.py` - Added streaming parameters to both search methods

### 4. Deployment Validation - RESOLVED
- **Problem**: Vespa deployment failed when changing indexing modes
- **Root Cause**: Missing validation override for `indexing-mode-change`
- **Fix**: Created `vespa/validation-overrides.xml` with 30-day override
- **Result**: Successfully deployed streaming mode configuration

### 5. Streaming Search Parameters Missing - RESOLVED ✅
- **Problem**: Search queries in VespaSearchTool and SemanticSearchTool were missing `streaming.groupname` parameter
- **Root Cause**: The search methods in `services/chat/agents/llm_tools.py` didn't include required streaming mode parameters
- **Fix**: Added `"streaming.groupname": self.user_id` to both `VespaSearchTool.search()` and `SemanticSearchTool.semantic_search()` methods
- **Result**: Interactive search mode now works without streaming errors
- **Files Modified**: `services/chat/agents/llm_tools.py` lines 335-340 and 598-603

## Current Critical Issue: Mock Data Generation 🚨

### **Problem**: System is generating fake/mock data instead of querying real office services
- **Root Cause**: `services/office/core/email_crawler.py` contains placeholder/mock data generation
- **Impact**: Users see fake emails like "Microsoft Email 1", "Microsoft Email 2" instead of real data
- **Location**: Lines 250-270 in `_get_microsoft_email_batch()` method

### **Evidence from Current System**:
```python
# Current mock data generation in email_crawler.py
emails.append({
    "id": email_id,
    "user_id": self.user_id,
    "provider": "microsoft",
    "type": "email",
    "subject": f"Microsoft Email {start_idx + i}",  # FAKE DATA
    "body": f"This is the body of Microsoft email {start_idx + i}",  # FAKE DATA
    "from": f"sender{i}@microsoft.com",  # FAKE DATA
    "to": [f"recipient{i}@example.com"],  # FAKE DATA
    # ... more fake data
})
```

### **What Should Happen Instead**:
```python
# Real implementation should look like:
from ..clients.microsoft_graph import MicrosoftGraphClient
client = MicrosoftGraphClient(self.user_id)

query_params = {
    "$top": batch_size,
    "$skip": batch_num * batch_size,
    "$orderby": "receivedDateTime desc"
}

if start_date:
    query_params["$filter"] = f"receivedDateTime ge {start_date.isoformat()}"
if end_date:
    if query_params.get("$filter"):
        query_params["$filter"] += f" and receivedDateTime le {end_date.isoformat()}"
    else:
        query_params["$filter"] = f"receivedDateTime le {end_date.isoformat()}"

emails = await client.get_emails(query_params)
return [self._normalize_microsoft_email(email) for email in emails]
```

### **Files Affected**:
- `services/office/core/email_crawler.py` - Main mock data generation
- `services/office/api/backfill.py` - Uses the mock email crawler
- `services/demos/vespa_backfill.py` - Calls the mock backfill API
- `services/demos/settings_demos.py` - Demo configuration that may enable mock mode

### **Immediate Action Required**:
1. **Stop using mock data** in production/demo scenarios
2. **Implement real Microsoft Graph API integration**
3. **Add proper authentication and API key management**
4. **Create demo mode toggle** to switch between real and mock data
5. **Update documentation** to clarify when mock vs real data is used

## Data Management Procedures

### How to Clear Data

#### Option 1: --clear-data (Recommended)
```bash
# From the root directory
./scripts/vespa.sh --clear-data
```

**What it does:**
- Queries Vespa for all documents using `select * from briefly_document where true`
- Extracts `doc_id` from each document
- Constructs proper streaming ID format: `id:briefly:briefly_document:g={user_id}:{doc_id}`
- Deletes each document individually
- Reports success/failure for each deletion

**Expected output:**
```
✅ Successfully deleted document: ms_9
✅ Successfully deleted document: ms_10
...
✅ All documents cleared successfully
```

#### Option 2: Nuclear Option (If --clear-data fails)
```bash
# Stop Vespa container and remove all data
./scripts/vespa.sh --stop
docker rm -f vespa-container
docker volume prune -f

# Restart fresh
./scripts/vespa.sh --start
./scripts/vespa.sh --deploy
```

### How to Run vespa_backfill.py

#### Basic Usage
```bash
# From the root directory
python services/demos/vespa_backfill.py trybriefly@outlook.com
```

#### What to Look For

**1. Document ID Generation**
✅ Good (Streaming Mode):
```
Indexing document with ID: id:briefly:briefly_document:g=trybriefly@outlook.com:ms_9
Indexing document with ID: id:briefly:briefly_document:g=trybriefly@outlook.com:ms_10
```

❌ Bad (Old Indexed Mode):
```
Indexing document with ID: id:briefly:briefly_document::ms_9
Indexing document with ID: id:briefly:briefly_document::ms_10
```

**2. Indexing Success**
✅ Good:
```
✅ Document indexed successfully: ms_9
✅ Document indexed successfully: ms_10
```

❌ Bad:
```
❌ Failed to index document: ms_9
❌ Failed to index document: ms_10
```

**3. Check for Duplicated IDs**
Look for any output showing:
```
id:briefly:briefly_document::id:briefly:briefly_document::ms_9
```
This indicates the old corruption issue.

## User ID Isolation Verification

### Method 1: Use vespa_search.py
```bash
# Search for documents as the correct user
python services/demos/vespa_search.py trybriefly@outlook.com --stats

# Try to search as a different user (should return no results)
python services/demos/vespa_search.py fakeuser@example.com --stats
```

**Expected Results:**
- `trybriefly@outlook.com` should return documents
- `fakeuser@example.com` should return 0 documents

### Method 2: Direct Vespa API Calls
```bash
# Search as correct user
curl -s "http://localhost:8080/search/" \
  -H "Content-Type: application/json" \
  -d '{
    "yql": "select * from briefly_document where true",
    "streaming.groupname": "trybriefly@outlook.com",
    "hits": 10
  }' | jq '.root.children | length'

# Search as different user (should return 0)
curl -s "http://localhost:8080/search/" \
  -H "Content-Type: application/json" \
  -d '{
    "yql": "select * from briefly_document where true",
    "streaming.groupname": "fakeuser@example.com",
    "hits": 10
  }' | jq '.root.children | length'
```

### Method 3: Check Document Structure
```bash
# Get a specific document to verify structure
curl -s "http://localhost:8080/document/v1/briefly/briefly_document/group/trybriefly@outlook.com/ms_9" | jq
```

**Expected Response:**
```json
{
  "pathId": "/document/v1/briefly/briefly_document/group/trybriefly@outlook.com/ms_9",
  "id": "id:briefly:briefly_document:g=trybriefly@outlook.com:ms_9",
  "fields": {
    "doc_id": "ms_9",
    "user_id": "trybriefly@outlook.com",
    "title": "...",
    "search_text": "..."
  }
}
```

## Complete Testing Workflow

### Test Sequence
```bash
# 1. Clear existing data
./scripts/vespa.sh --clear-data

# 2. Verify data is cleared
python services/demos/vespa_search.py trybriefly@outlook.com --stats
# Should return: "Found 0 documents"

# 3. Run backfill to populate fresh data
python services/demos/vespa_backfill.py trybriefly@outlook.com

# 4. Verify data is populated
python services/demos/vespa_search.py trybriefly@outlook.com --stats
# Should return: "Found X documents"

# 5. Test user isolation
python services/demos/vespa_search.py fakeuser@example.com --stats
# Should return: "Found 0 documents"

# 6. Clear data again to verify --clear-data works
./scripts/vespa.sh --clear-data

# 7. Final verification
python services/demos/vespa_search.py trybriefly@outlook.com --stats
# Should return: "Found 0 documents"
```

## Issues to Watch For

### 1. PathId vs ID Confusion
**Problem:** Vespa responses have both `pathId` and `id` fields
- `pathId`: Full URL path (e.g., `/document/v1/briefly/briefly_document/group/user@example.com/doc123`)
- `id`: Document identifier (e.g., `id:briefly:briefly_document:g=user@example.com:doc123`)

**Solution:** Use `id` field for document operations, `pathId` for verification

### 2. Duplicated ID Corruption
**Problem:** Old documents might have corrupted IDs like:
```
id:briefly:briefly_document::id:briefly:briefly_document::ms_9
```

**Solution:** Clear all data and re-index with streaming mode

### 3. User ID Field Presence
**Problem:** Documents might be missing `user_id` field
**Solution:** In streaming mode, `user_id` is automatically extracted from document ID

## Remaining Tasks to Complete

### 1. Test Suite Cleanup - MEDIUM PRIORITY
- [x] Fix the user isolation test that's returning 400 errors (RESOLVED - streaming parameters added)
- [ ] Ensure all tests use consistent streaming mode parameters (tests need streaming.groupname added)
- [ ] Add more comprehensive error handling tests

### 2. Error Handling - MEDIUM PRIORITY
- [ ] Better error messages for streaming mode failures
- [ ] Graceful fallback when streaming parameters are missing
- [ ] Clear documentation of streaming mode requirements

### 3. Performance Optimization - LOW PRIORITY
- [ ] Optimize streaming search queries for large datasets
- [ ] Consider batch operations for document management
- [ ] Monitor memory usage with streaming mode

### 4. Production Readiness - MEDIUM PRIORITY
- [ ] Validate streaming mode works with production data volumes
- [ ] Test user isolation under load
- [ ] Document deployment procedures for streaming mode

### 5. Monitoring & Alerting - LOW PRIORITY
- [ ] Add alerts for user isolation failures
- [ ] Monitor document ID corruption
- [ ] Track streaming mode performance metrics

### 6. REAL DATA INTEGRATION - HIGH PRIORITY 🚨
- [ ] **Replace mock data generation with real Microsoft Graph API integration**
  - [ ] Implement real Microsoft Graph client in `services/office/core/email_crawler.py`
  - [ ] Remove placeholder/mock email generation in `_get_microsoft_email_batch()`
  - [ ] Add proper authentication and API key management for Microsoft Graph
  - [ ] Implement real email crawling with proper rate limiting and error handling
- [ ] **Implement real Gmail API integration**
  - [ ] Create Gmail client in `services/office/core/email_crawler.py`
  - [ ] Remove placeholder Gmail email generation
  - [ ] Add OAuth2 authentication flow for Gmail API access
- [ ] **Add real calendar and contact data integration**
  - [ ] Implement Microsoft Graph calendar API integration
  - [ ] Implement Microsoft Graph contacts API integration
  - [ ] Add Gmail calendar and contacts API integration
- [ ] **Create data source configuration system**
  - [ ] Add environment variables for API keys and endpoints
  - [ ] Create configuration for different data sources (Microsoft, Google, etc.)
  - [ ] Add demo mode toggle to switch between real and mock data
- [ ] **Implement proper error handling for real API calls**
  - [ ] Handle API rate limiting and quotas
  - [ ] Add retry logic for transient failures
  - [ ] Implement fallback mechanisms when APIs are unavailable
- [ ] **Add data validation and quality checks**
  - [ ] Validate email structure and content
  - [ ] Check for data consistency across different sources
  - [ ] Implement data sanitization and normalization

## Success Criteria

The system will work flawlessly when:
1. ✅ `--clear-data` successfully removes all documents
2. ✅ `vespa_backfill.py` indexes documents with correct streaming IDs
3. ✅ User isolation prevents cross-user document access
4. ✅ All tests pass consistently
5. ✅ No ID corruption or duplication occurs
6. ✅ Streaming mode performance is acceptable
7. ✅ Error handling is robust and informative
8. ✅ **Real office service data is integrated** (not mock data)
9. ✅ **Microsoft Graph API provides real emails, calendar, and contacts**
10. ✅ **Gmail API provides real emails, calendar, and contacts**
11. ✅ **Demo mode can toggle between real and mock data for testing**
12. ✅ **Authentication and API key management is properly implemented**

## Current Status: 🚨 MOCK DATA ISSUE IDENTIFIED

**Latest Critical Issue Discovered (2025-08-17):**
- 🚨 **CRITICAL**: System is generating fake/mock data instead of querying real office services
- 🚨 **ROOT CAUSE**: `services/office/core/email_crawler.py` contains placeholder/mock data generation
- 🚨 **IMPACT**: Users see fake emails like "Microsoft Email 1", "Microsoft Email 2" instead of real data
- 🚨 **LOCATION**: Lines 250-270 in `_get_microsoft_email_batch()` method

**Previous Fixes Completed:**
- ✅ Fixed streaming search parameters missing in VespaSearchTool and SemanticSearchTool
- ✅ Interactive search mode now works without "Streaming search requires streaming.groupname" errors
- ✅ Both direct query mode and interactive mode are functional
- ✅ User isolation maintained through streaming mode parameters

**Next Priority - REAL DATA INTEGRATION:**
- 🚨 **IMMEDIATE**: Replace mock data generation with real Microsoft Graph API integration
- 🚨 **IMMEDIATE**: Implement real Gmail API integration
- 🚨 **IMMEDIATE**: Add proper authentication and API key management
- 🚨 **IMMEDIATE**: Create demo mode toggle to switch between real and mock data
- 🚨 **IMMEDIATE**: Stop using mock data in production/demo scenarios

## Next Steps Priority

1. **✅ COMPLETED:** Fix the user isolation test 400 error (streaming parameters added)
2. **High:** Verify `--clear-data` works end-to-end
3. **High:** Test complete workflow (clear → backfill → verify isolation → clear)
4. **Medium:** Clean up test suite and add comprehensive error tests
5. **Low:** Performance optimization and production readiness

## Technical Notes

### Vespa Streaming Mode Requirements
- `mode="streaming"` in the schema configuration
- Document IDs in format: `id:myNamespace:myType:g=myUserid:myLocalid`
- Search queries using `streaming.groupname` parameter for user isolation
- URL paths like `/document/v1/myNamespace/myType/group/myUserId/myLocalId`

### Key Files Modified
- `vespa/services.xml` - Changed indexing mode to streaming
- `vespa/validation-overrides.xml` - Added indexing mode change override
- `services/vespa_loader/vespa_client.py` - Updated ID generation and API calls
- `scripts/vespa.sh` - Fixed clear-data functionality and deployment logic

### Test Files Created
- `scripts/test_vespa_integration.py` - Comprehensive integration test runner
- `services/vespa_loader/tests/test_vespa_client_integration.py` - Client lifecycle tests
- `services/vespa_loader/tests/test_document_indexing.py` - Document indexing tests
- `services/vespa_loader/tests/test_search_consistency.py` - Search consistency tests
- `services/vespa_loader/tests/test_user_isolation.py` - User isolation tests

## Security Impact

**Before:** 
- No user isolation - documents could be accessed by any user
- Critical security vulnerability for multi-tenant application

**After:** 
- User isolation enforced at Vespa level through streaming mode
- Documents automatically isolated by user through group-based access control
- Security compliance restored

## Lessons Learned

1. **Vespa configuration is critical** - the difference between indexed and streaming modes affects core functionality
2. **User isolation must be designed into the system** from the beginning, not added later
3. **Automated testing is essential** for catching configuration and data structure issues
4. **Documentation matters** - Vespa's streaming mode requirements were the key to solving the problem
5. **Validation overrides** are necessary when making significant configuration changes

---

*This document should be updated as we complete tasks and discover new issues.*
