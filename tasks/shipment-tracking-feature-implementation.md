# Shipment Tracking Feature Implementation Task List

## Overview
Implement a shipment tracking feature that allows users to track packages directly from email cards using a magic wand button. The feature includes automatic detection of tracking information, user data correction, and optional data collection for service improvements.

## Phase 1: Frontend Magic Wand Button Implementation

### Task 1.1: Update Email Card Component
**File:** `frontend/components/email/email-card.tsx`
**Priority:** High
**Estimated Time:** 2-3 hours

**Requirements:**
- Remove the existing download button from email cards
- Add a magic wand button (✨) in the upper-right corner of each email card
- Implement a dropdown menu for the magic wand button
- Move the download functionality to the dropdown menu as "Download Email"
- Add "Track Shipment" option to the dropdown menu

**Implementation Details:**
- Use Lucide React icons for the magic wand and dropdown arrow
- Implement dropdown state management with React hooks
- Style the button with proper hover states and accessibility
- Ensure the dropdown is properly positioned and doesn't overflow

**Acceptance Criteria:**
- [x] Magic wand button appears in upper-right corner of each email card
- [x] Clicking the wand opens a dropdown menu
- [x] Dropdown contains "Download Email" and "Track Shipment" options
- [x] Download functionality works as before
- [x] Button is accessible with proper ARIA labels
- [x] Dropdown closes when clicking outside

### Task 1.2: Implement Shipment Detection Logic
**File:** `frontend/hooks/use-shipment-detection.ts`
**Priority:** High
**Estimated Time:** 3-4 hours

**Requirements:**
- Create a custom hook for detecting shipment information in emails
- Check for common shipment email patterns (amazon.com, ups.com, etc.)
- Detect tracking numbers using regex patterns
    - Use learnings from services/shipments/email_parser.py in git branch "shipments-email-parsing"
- Implement heuristics for detecting tracking numbers and shipment emails
- Return detection status

**Implementation Details:**
- Create regex patterns for common tracking number formats
- Implement sender domain checking for known carriers
- Add subject line analysis for shipment keywords
- Return structured detection results

**Acceptance Criteria:**
- [x] Hook correctly identifies Amazon shipment emails
- [x] Hook detects UPS, FedEx, USPS tracking numbers
- [x] Hook handles edge cases gracefully
- [x] Performance is optimized for real-time use

### Task 1.3: Update Email Card with Detection
**File:** `frontend/components/email/email-card.tsx`
**Priority:** High
**Estimated Time:** 1-2 hours

**Requirements:**
- Integrate shipment detection hook into email card
- Color the "Track Shipment" menu item based on detection status
- Show visual indicators when shipment is detected

**Implementation Details:**
- Use the detection hook to analyze each email
- Apply conditional styling to the "Track Shipment" option
- Add loading states during detection

**Acceptance Criteria:**
- [x] "Track Shipment" option is colored when detection is positive
- [x] Visual feedback is immediate and clear
- [x] No performance impact on email list rendering

## Phase 2: Backend Email Parser Integration

### Task 2.1: Create Email Parser Endpoint
**File:** `services/shipments/routers/email_parser.py`
**Priority:** High
**Estimated Time:** 4-5 hours

**Requirements:**
- Create a new router for email parsing functionality
- Implement POST endpoint `/api/v1/email-parser/parse`
- Integrate with existing `EmailParser` class
- Handle email content from frontend
- Return structured parsing results

**Implementation Details:**
- Create new router file with proper FastAPI structure
- Use existing `EmailParser` from `services/shipments/email_parser.py`
- Implement proper request/response schemas
- Add error handling and validation
- Include authentication and rate limiting

**Acceptance Criteria:**
- [x] Endpoint accepts email subject, sender, and body
- [x] Returns structured tracking information
- [x] Handles various email formats correctly
- [x] Includes proper error responses
- [x] Performance is acceptable for real-time use

### Task 2.2: Update Shipments Service Router
**File:** `services/shipments/routers/__init__.py`
**Priority:** Medium
**Estimated Time:** 1 hour

**Requirements:**
- Add email parser router to the main API router
- Update router imports and configuration

**Implementation Details:**
- Import the new email parser router
- Add it to the main API router with proper prefix
- Update tags for API documentation

**Acceptance Criteria:**
- [x] Email parser endpoints are accessible via `/api/v1/email-parser/*`
- [x] Router is properly integrated with authentication
- [x] API documentation is updated

### Task 2.3: Create Request/Response Schemas
**File:** `services/shipments/schemas/email_parser.py`
**Priority:** Medium
**Estimated Time:** 2 hours

**Requirements:**
- Define Pydantic schemas for email parser requests and responses
- Include validation for required fields
- Provide proper documentation and examples

**Implementation Details:**
- Create `EmailParseRequest` schema
- Create `EmailParseResponse` schema
- Include all fields from `ParsedEmailData`
- Add proper field validation and descriptions

**Acceptance Criteria:**
- [x] Schemas validate input data correctly
- [x] Response includes all necessary tracking fields
- [x] Documentation is clear and complete
- [x] Examples are provided for testing

## Phase 3: Frontend Modal and Data Collection

### Task 3.1: Create Track Shipment Modal
**File:** `frontend/components/email/track-shipment-modal.tsx`
**Priority:** High
**Estimated Time:** 4-5 hours

**Requirements:**
- Create a modal component for tracking shipment details
- Display auto-detected information in form fields
- Allow users to edit/correct the information
- Include form validation
- Provide "Track" and "Cancel" actions

**Implementation Details:**
- Use existing UI components (Modal, Form, Input, etc.)
- Pre-populate fields with parsed data
- Implement form validation for required fields
- Handle loading states during API calls
- Provide clear error messages

**Acceptance Criteria:**
- [x] Modal opens when "Track Shipment" is clicked
- [x] Form fields are pre-populated with detected data
- [x] Users can edit all fields
- [x] Validation prevents submission of invalid data
- [x] Modal closes properly on cancel/success

### Task 3.2: Implement Frontend API Integration
**File:** `frontend/lib/shipments-client.ts`
**Priority:** High
**Estimated Time:** 2-3 hours

**Requirements:**
- Create API client for shipments service
- Implement email parsing endpoint call
- Handle authentication and error responses
- Provide TypeScript types for responses

**Implementation Details:**
- Extend existing gateway client pattern
- Add methods for email parsing and package creation
- Include proper error handling
- Add TypeScript interfaces for all data structures

**Acceptance Criteria:**
- [x] API client can call email parser endpoint
- [x] Proper error handling for network issues
- [x] TypeScript types are complete and accurate
- [x] Authentication is handled correctly

### Task 3.3: Integrate Modal with Email Card
**File:** `frontend/components/email/email-card.tsx`
**Priority:** High
**Estimated Time:** 2-3 hours

**Requirements:**
- Connect magic wand "Track Shipment" action to modal
- Pass email data to modal component
- Handle modal state management
- Implement success/error feedback

**Implementation Details:**
- Add modal state to email card component
- Pass email data as props to modal
- Handle modal open/close logic
- Show success/error messages after tracking

**Acceptance Criteria:**
- [x] Clicking "Track Shipment" opens the modal
- [x] Email data is passed correctly to modal
- [x] Modal state is managed properly
- [x] User gets feedback on success/failure

## Phase 4: Data Collection and User Preferences

### Task 4.1: Add Shipment Data Collection Preference
**File:** `services/user/schemas/preferences.py`
**Priority:** Medium
**Estimated Time:** 1-2 hours

**Requirements:**
- Add shipment data collection preference to privacy settings
- Include in user preferences schema
- Provide default value (enabled)

**Implementation Details:**
- Add `shipment_data_collection` field to `PrivacyPreferencesSchema`
- Set default value to `True`
- Update documentation and examples

**Acceptance Criteria:**
- [x] New preference field is added to schema
- [x] Default value is enabled
- [x] Documentation is updated
- [x] Migration handles existing users

### Task 4.2: Create Data Collection Endpoint
**File:** `services/shipments/routers/data_collection.py`
**Priority:** Medium
**Estimated Time:** 3-4 hours

**Requirements:**
- Create endpoint for collecting user-corrected shipment data
- Store auto-generated data, user corrections, and original email
- Include user consent validation
- Implement data anonymization if needed

**Implementation Details:**
- Create new router for data collection
- Implement POST endpoint for storing training data
- Include user ID and consent validation
- Store structured data for future model improvements

**Acceptance Criteria:**
- [x] Endpoint accepts user-corrected data
- [x] Stores both auto-generated and user data
- [x] Validates user consent before storing
- [x] Data is stored securely and anonymously

### Task 4.3: Update Frontend to Check User Preferences
**File:** `frontend/components/email/track-shipment-modal.tsx`
**Priority:** Medium
**Estimated Time:** 2-3 hours

**Requirements:**
- Check user's shipment data collection preference
- Submit data to collection endpoint if enabled
- Provide clear feedback about data usage

**Implementation Details:**
- Use user preferences context to check consent
- Call data collection endpoint when tracking is successful
- Show user-friendly message about data usage
- Handle cases where consent is not given

**Acceptance Criteria:**
- [x] User preference is checked before data collection
- [x] Data is only sent if user has consented
- [x] User is informed about data usage
- [x] Graceful handling when consent is not given

## Phase 5: Testing and Quality Assurance

### Task 5.1: Frontend Component Testing
**Files:** `frontend/components/email/__tests__/`
**Priority:** Medium
**Estimated Time:** 3-4 hours

**Requirements:**
- Write unit tests for email card component
- Test magic wand button functionality
- Test shipment detection hook
- Test modal component behavior

**Implementation Details:**
- Use Jest and React Testing Library
- Mock API calls and user preferences
- Test all user interactions
- Verify accessibility features

**Acceptance Criteria:**
- [ ] All components have >80% test coverage
- [ ] User interactions are properly tested
- [ ] Error states are handled correctly
- [ ] Accessibility features are verified

### Task 5.2: Backend API Testing
**Files:** `services/shipments/tests/test_email_parser_api.py`
**Priority:** Medium
**Estimated Time:** 2-3 hours

**Requirements:**
- Test email parser endpoint with various email formats
- Test error handling and validation
- Test data collection endpoint
- Verify authentication and permissions

**Implementation Details:**
- Use pytest for backend testing
- Test with real email samples
- Verify response formats and error codes
- Test rate limiting and security

**Acceptance Criteria:**
- [ ] All endpoints are properly tested
- [ ] Error cases are covered
- [ ] Authentication is verified
- [ ] Performance is acceptable

### Task 5.3: Integration Testing
**Files:** `tests/integration/test_shipment_tracking.py`
**Priority:** Medium
**Estimated Time:** 3-4 hours

**Requirements:**
- Test complete flow from email to tracking
- Test data collection with user preferences
- Test error scenarios and edge cases
- Verify end-to-end functionality

**Implementation Details:**
- Create integration tests that test the full flow
- Mock external services appropriately
- Test with various email formats and carriers
- Verify data consistency across services

**Acceptance Criteria:**
- [ ] Complete user flow works end-to-end
- [ ] Data collection works correctly
- [ ] Error handling is robust
- [ ] Performance meets requirements

## Phase 6: Documentation and Deployment

### Task 6.1: Update API Documentation
**Files:** Various documentation files
**Priority:** Low
**Estimated Time:** 2-3 hours

**Requirements:**
- Update API documentation for new endpoints
- Document the shipment tracking feature
- Provide usage examples and best practices
- Update OpenAPI/Swagger documentation

**Implementation Details:**
- Add endpoint documentation to relevant files
- Create feature overview documentation
- Include code examples and use cases
- Update API versioning documentation

**Acceptance Criteria:**
- [ ] All new endpoints are documented
- [ ] Examples are clear and working
- [ ] Documentation is up-to-date
- [ ] API versioning is properly documented

### Task 6.2: Update Gateway Configuration
**File:** `gateway/express_gateway.tsx`
**Priority:** Low
**Estimated Time:** 1 hour

**Requirements:**
- Add email parser routes to gateway
- Update service routing configuration
- Ensure proper authentication flow

**Implementation Details:**
- Add email parser routes to service routes
- Update proxy configuration
- Verify authentication middleware

**Acceptance Criteria:**
- [x] Email parser endpoints are accessible through gateway
- [x] Authentication works correctly
- [x] Routing is properly configured
- [x] No breaking changes to existing functionality

### Task 6.3: Update Frontend API Client
**File:** `frontend/lib/gateway-client.ts`
**Priority:** Low
**Estimated Time:** 1-2 hours

**Requirements:**
- Add shipment tracking methods to gateway client
- Update TypeScript types
- Ensure proper error handling

**Implementation Details:**
- Add methods for email parsing and data collection
- Update TypeScript interfaces

**Acceptance Criteria:**
- [x] Email parser client methods are implemented
- [x] Data collection client methods are implemented
- [x] TypeScript types are properly defined
- [x] Error handling is comprehensive

## Phase 7: Secure Endpoints

### Task 7.1: Add User Authentication to Shipments Service
**Files:** `services/shipments/auth/`, `services/shipments/main.py`
**Priority:** High
**Estimated Time:** 3-4 hours

**Requirements:**
- Implement user authentication middleware following user service patterns
- Support both gateway headers (X-User-Id) and JWT tokens
- Add user ownership validation for package resources
- Ensure data isolation between users

**Implementation Details:**
- Create `services/shipments/auth/` directory with authentication modules
- Implement `get_current_user_from_gateway_headers()` function
- Implement `get_current_user_flexible()` for dual authentication support
- Add `verify_user_ownership()` and `require_user_ownership()` functions
- Update main.py to include user authentication middleware
- Follow the same patterns as user service authentication

**Acceptance Criteria:**
- [x] User authentication middleware is implemented
- [x] Gateway header extraction works correctly
- [x] JWT token fallback works correctly
- [x] User ownership validation functions are available
- [x] Authentication follows established patterns

### Task 7.2: Secure Email Parser Endpoint
**File:** `services/shipments/routers/email_parser.py`
**Priority:** High
**Estimated Time:** 1-2 hours

**Requirements:**
- Add user authentication to email parser endpoint
- Validate user ownership of email data
- Ensure proper access control for email parsing

**Implementation Details:**
- Add `get_current_user` dependency to parse_email endpoint
- Extract user_id from email data or request context
- Add user ownership validation for email access
- Update error handling for authentication failures
- Ensure email data belongs to authenticated user

**Acceptance Criteria:**
- [x] Email parser requires user authentication
- [x] User ownership of email data is validated
- [x] Proper error responses for unauthorized access
- [x] API key authentication still works for service-to-service calls

### Task 7.3: Secure Data Collection Endpoint
**File:** `services/shipments/routers/data_collection.py`
**Priority:** High
**Estimated Time:** 1-2 hours

**Requirements:**
- Add user authentication to data collection endpoint
- Validate user ownership of collected data
- Ensure user consent validation is secure

**Implementation Details:**
- Add `get_current_user` dependency to collect_shipment_data endpoint
- Validate that user_id in request matches authenticated user
- Add user ownership validation for data collection
- Ensure consent validation is tied to authenticated user
- Update error handling for authentication and ownership failures

**Acceptance Criteria:**
- [x] Data collection requires user authentication
- [x] User ownership of data is validated
- [x] Consent validation is secure and user-specific
- [x] Proper error responses for unauthorized access

### Task 7.4: Secure Package Management Endpoints
**Files:** `services/shipments/routers/labels.py`, `services/shipments/routers/carrier_configs.py`
**Priority:** High
**Estimated Time:** 2-3 hours

**Requirements:**
- Add user authentication to all package management endpoints
- Validate user ownership of packages and labels
- Ensure proper access control for carrier configurations

**Implementation Details:**
- Add `get_current_user` dependency to all package endpoints
- Implement user ownership validation for packages
- Add user ownership validation for labels
- Ensure carrier configs are user-specific or properly secured
- Update all CRUD operations to validate user ownership
- Add proper error handling for unauthorized access

**Acceptance Criteria:**
- [x] All package endpoints require user authentication
- [x] User ownership of packages is validated
- [x] User ownership of labels is validated
- [x] Carrier configurations are properly secured
- [x] Proper error responses for unauthorized access

### Task 7.5: Add User Context to Package Models
**Files:** `services/shipments/models/`, `services/shipments/database.py`
**Priority:** Medium
**Estimated Time:** 2-3 hours

**Requirements:**
- Ensure all package models include user_id field
- Add database constraints for user ownership
- Update database migrations if needed

**Implementation Details:**
- Verify Package model has user_id field with proper constraints
- Verify Label model has user_id field with proper constraints
- Add database indexes for user_id fields for performance
- Update any existing migrations to include user_id constraints
- Ensure foreign key relationships are properly defined

**Acceptance Criteria:**
- [ ] All package models have user_id fields
- [ ] Database constraints enforce user ownership
- [ ] Proper indexes exist for user_id fields
- [ ] Foreign key relationships are correctly defined

### Task 7.6: Update API Key Configuration
**File:** `services/shipments/service_auth.py`
**Priority:** Medium
**Estimated Time:** 1 hour

**Requirements:**
- Update API key permissions to include user-specific operations
- Ensure proper separation between service-to-service and user-facing operations

**Implementation Details:**
- Review and update API key permissions for user-specific operations
- Ensure frontend has appropriate permissions for user operations
- Add any missing permissions for data collection and email parsing
- Update permission documentation

**Acceptance Criteria:**
- [ ] API key permissions are properly configured
- [ ] Frontend has appropriate permissions for user operations
- [ ] Service-to-service permissions are properly separated
- [ ] Permission documentation is updated

### Task 7.7: Security Testing
**Files:** `services/shipments/tests/test_security.py`
**Priority:** High
**Estimated Time:** 2-3 hours

**Requirements:**
- Test user authentication and authorization
- Test user ownership validation
- Test API key authentication
- Test unauthorized access scenarios

**Implementation Details:**
- Create comprehensive security test suite
- Test authentication with both gateway headers and JWT tokens
- Test user ownership validation for all resources
- Test unauthorized access attempts
- Test API key authentication for service-to-service calls
- Test cross-user access attempts

**Acceptance Criteria:**
- [ ] User authentication tests pass
- [ ] User ownership validation tests pass
- [ ] API key authentication tests pass
- [ ] Unauthorized access is properly blocked
- [ ] Cross-user access is properly blocked
- Maintain consistency with existing patterns

**Acceptance Criteria:**
- [x] New methods are available in gateway client
- [x] TypeScript types are complete
- [x] Error handling is consistent
- [x] No breaking changes to existing functionality

## Implementation Timeline

### Week 1: Frontend Foundation
- Task 1.1: Update Email Card Component
- Task 1.2: Implement Shipment Detection Logic
- Task 1.3: Update Email Card with Detection

### Week 2: Backend Integration
- Task 2.1: Create Email Parser Endpoint
- Task 2.2: Update Shipments Service Router
- Task 2.3: Create Request/Response Schemas

### Week 3: Frontend Modal and API
- Task 3.1: Create Track Shipment Modal
- Task 3.2: Implement Frontend API Integration
- Task 3.3: Integrate Modal with Email Card

### Week 4: Data Collection
- Task 4.1: Add Shipment Data Collection Preference
- Task 4.2: Create Data Collection Endpoint
- Task 4.3: Update Frontend to Check User Preferences

### Week 5: Testing and Documentation
- Task 5.1: Frontend Component Testing
- Task 5.2: Backend API Testing
- Task 5.3: Integration Testing
- Task 6.1: Update API Documentation

### Week 6: Deployment
- Task 6.2: Update Gateway Configuration
- Task 6.3: Update Frontend API Client

## Success Metrics

### Functional Requirements
- [ ] Users can track shipments from email cards
- [ ] Automatic detection works for major carriers
- [ ] Users can correct auto-detected information
- [ ] Data collection respects user preferences
- [ ] Feature works across different email providers

### Performance Requirements
- [ ] Email detection completes in <500ms
- [ ] Modal opens in <200ms
- [ ] API responses complete in <2s
- [ ] No impact on email list rendering performance

### Quality Requirements
- [ ] >90% test coverage for new components
- [ ] All accessibility requirements met
- [ ] Error handling covers all edge cases
- [ ] Documentation is complete and accurate

## Risk Mitigation

### Technical Risks
- **Email parsing accuracy**: Use existing robust parser with fallback to LLM
- **Performance impact**: Implement lazy loading and caching
- **Browser compatibility**: Test across major browsers

### User Experience Risks
- **False positives**: Provide clear visual feedback and allow easy dismissal
- **Complexity**: Keep UI simple and intuitive
- **Privacy concerns**: Clear consent and data usage communication

### Integration Risks
- **Service dependencies**: Implement proper error handling and fallbacks
- **API versioning**: Follow existing patterns and maintain backward compatibility
- **Data consistency**: Implement proper validation and error recovery 