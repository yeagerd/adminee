# Update Frontend Contacts Tool for Bi-Contact Source Concept

## Overview
The Contacts Service now provides a unified view of contacts from two sources:
1. **Office Contacts** - Synced from Google/Microsoft (via Office Service read-through)
2. **Discovered Contacts** - Automatically discovered from email, calendar, and document events

The frontend needs to be updated to represent and manage this bi-source concept with proper CRUD operations.

## Current Architecture Analysis

### ✅ What's Already Working
- [x] Gateway routes `/api/v1/contacts/*` to Contacts Service (port 8007)
- [x] Contacts Service has read-through to Office Service for office integration data
- [x] Contact models support `source_services` field to track origin
- [x] Office integration service enriches contacts with provider data
- [x] Frontend has basic contact display components
- [x] TypeScript types exist for both old Office contacts and new Contacts Service

### 🔄 Current Data Flow
1. Frontend calls `/api/v1/contacts` (now routed to Contacts Service)
2. Contacts Service fetches discovered contacts from database
3. Contacts Service calls Office Service to get office integration data
4. Contacts Service merges data and returns unified response
5. Frontend displays contacts with source indicators

## Tasks

### Phase 1: Complete Frontend Rewrite for New Data Structure
- [ ] **Remove Old Office Contact Types** - Delete obsolete type definitions
  - [ ] Delete `frontend/types/api/office/models/Contact.ts`
  - [ ] Delete `frontend/types/api/office/models/ContactPhone.ts`
  - [ ] Delete `frontend/types/api/office/models/EmailAddress.ts`
  - [ ] Update `frontend/types/api/office/index.ts` to remove contact exports
  - [ ] Update `frontend/types/api/office/models/ContactCreateResponse.ts`
  - [ ] Update `frontend/types/api/office/models/ContactDeleteResponse.ts`
  - [ ] Update `frontend/types/api/office/models/ContactList.ts`
  - [ ] Update `frontend/types/api/office/models/ContactUpdateResponse.ts`

- [ ] **Update Office Client** - Complete rewrite of `frontend/api/clients/office-client.ts`
  - [ ] Remove all contact-related methods (getContacts, updateContact, createContact, deleteContact)
  - [ ] Remove contact-related imports and types
  - [ ] Keep only calendar, email, and file operations
  - [ ] Update method signatures to remove contact dependencies

- [ ] **Create New Contacts Service Client** - New file `frontend/api/clients/contacts-client.ts`
  - [ ] Implement `getContacts(limit, offset, tags, source_services, query)` method
  - [ ] Implement `searchContacts(query, limit, tags, source_services)` method
  - [ ] Implement `createContact(contactData)` method
  - [ ] Implement `updateContact(id, contactData)` method
  - [ ] Implement `deleteContact(id)` method
  - [ ] Implement `getContactStats()` method
  - [ ] Add proper error handling and response typing

- [ ] **Update API Index** - Modify `frontend/api/index.ts`
  - [ ] Remove `officeApi` export
  - [ ] Add `contactsApi` export
  - [ ] Update any existing imports that reference office API for contacts

### Phase 2: Complete Component Rewrite for New Data Structure
- [ ] **Rewrite Contacts View Component** - Complete rewrite of `frontend/components/views/contacts-view.tsx`
  - [ ] Replace all `officeApi.getContacts()` calls with `contactsApi.getContacts()`
  - [ ] Update state management to use new contact structure
  - [ ] Remove old contact filtering logic (company, provider-based)
  - [ ] Implement new filtering by source_services, tags, relevance_score
  - [ ] Update contact display to show source services and relevance data
  - [ ] Remove old contact card rendering logic
  - [ ] Implement new contact card component with source indicators

- [ ] **Create New Contact Card Component** - New file `frontend/components/contacts/contact-card.tsx`
  - [ ] Display contact name, email, and source services
  - [ ] Show relevance score and event counts
  - [ ] Add source service badges (Office, Email, Calendar, Documents)
  - [ ] Include office integration status indicators
  - [ ] Add quick action buttons (edit, delete, merge)

- [ ] **Create Contact Filters Component** - New file `frontend/components/contacts/contact-filters.tsx`
  - [ ] Source service filter (Office, Discovered, Both)
  - [ ] Provider filter (Google, Microsoft)
  - [ ] Relevance score range slider
  - [ ] Event type filter (Email, Calendar, Documents)
  - [ ] Tags filter with multi-select
  - [ ] Search input for name/email/notes

- [ ] **Create Contact Actions Component** - New file `frontend/components/contacts/contact-actions.tsx`
  - [ ] Add contact button
  - [ ] Bulk actions (delete, tag, export)
  - [ ] Refresh contacts button
  - [ ] Discovery settings button

### Phase 3: CRUD Operations and Forms
- [ ] **Create Contact Form Component** - New file `frontend/components/contacts/contact-form.tsx`
  - [ ] Form for creating new contacts
  - [ ] Source selection (Office sync vs Local only)
  - [ ] Provider selection for office contacts (Google/Microsoft)
  - [ ] Contact details input (name, email, phone, address, notes)
  - [ ] Tags input with autocomplete
  - [ ] Form validation and error handling

- [ ] **Edit Contact Form Component** - New file `frontend/components/contacts/edit-contact-form.tsx`
  - [ ] Pre-populated form for editing existing contacts
  - [ ] Handle different update scenarios based on source
  - [ ] Conflict resolution for office vs discovered data
  - [ ] Merge options for duplicate contacts
  - [ ] Source service management

- [ ] **Contact Detail Modal** - New file `frontend/components/contacts/contact-detail-modal.tsx`
  - [ ] Full contact information display
  - [ ] Event history and counts
  - [ ] Office integration status and sync info
  - [ ] Edit and delete actions
  - [ ] Source service breakdown

### Phase 4: Advanced Features and Management
- [ ] **Contact Discovery Management** - New file `frontend/components/contacts/discovery-settings.tsx`
  - [ ] Enable/disable discovery for specific event types
  - [ ] Discovery frequency settings
  - [ ] Discovery history and logs
  - [ ] Manual discovery trigger
  - [ ] Discovery performance metrics

- [ ] **Contact Merging Interface** - New file `frontend/components/contacts/contact-merger.tsx`
  - [ ] Duplicate detection and suggestions
  - [ ] Manual merge interface
  - [ ] Merge conflict resolution
  - [ ] Merge history tracking
  - [ ] Bulk merge operations

- [ ] **Contact Analytics Dashboard** - New file `frontend/components/contacts/analytics-dashboard.tsx`
  - [ ] Contact source distribution charts
  - [ ] Discovery trends over time
  - [ ] Relevance score analysis
  - [ ] Office sync status dashboard
  - [ ] Contact growth metrics

### Phase 5: Testing and Validation
- [ ] **Unit Tests** - Component and utility testing
  - [ ] Test new contact components with new data structure
  - [ ] Test contact filtering and search logic
  - [ ] Test CRUD operations with new API
  - [ ] Test error handling and edge cases
  - [ ] Test contact merging logic
  - [ ] Test discovery management functionality

- [ ] **Integration Tests** - End-to-end testing
  - [ ] Test complete contact workflow with Contacts Service
  - [ ] Test office integration scenarios
  - [ ] Test contact discovery flow
  - [ ] Test data consistency across operations
  - [ ] Test performance with large contact lists

- [ ] **User Acceptance Testing** - Real-world validation
  - [ ] Test with actual Google/Microsoft accounts
  - [ ] Validate contact discovery accuracy
  - [ ] Test new UI components and workflows
  - [ ] Validate user experience improvements

### Phase 6: Cleanup and Documentation
- [ ] **Remove Obsolete Code** - Clean up old contact-related code
  - [ ] Remove old contact types from office API
  - [ ] Clean up any remaining imports of old contact types
  - [ ] Remove unused contact-related utilities
  - [ ] Update any remaining references to old contact structure

- [ ] **Update Documentation** - Document new contact system
  - [ ] Update component documentation
  - [ ] Document new API endpoints and data structures
  - [ ] Create user guide for new contact features
  - [ ] Document contact discovery and merging workflows

- [ ] **Performance Optimization** - Optimize new contact system
  - [ ] Implement virtual scrolling for large contact lists
  - [ ] Add contact data caching
  - [ ] Optimize search and filtering performance
  - [ ] Add loading states and skeleton screens

## Implementation Notes

### Complete Frontend Rewrite Strategy
Instead of data transformation, we're completely rewriting the frontend to use the new data structure directly. This approach:

1. **Eliminates Technical Debt** - No more legacy contact type handling
2. **Improves Performance** - Direct use of new API responses
3. **Better User Experience** - Native support for new features
4. **Easier Maintenance** - Single source of truth for contact data
5. **Future-Proof** - Easy to add new contact sources and features

### New Data Structure Usage
The frontend will directly use the Contacts Service data structure:

```typescript
// Direct usage of new contact structure
interface Contact {
  id?: string;
  user_id: string;
  email_address: string;
  display_name?: string;
  given_name?: string;
  family_name?: string;
  source_services: string[];
  event_counts: Record<string, EmailContactEventCount>;
  total_event_count: number;
  relevance_score: number;
  last_seen: string;
  first_seen: string;
  tags: string[];
  notes?: string;
  created_at: string;
  updated_at: string;
}
```

### Source Service Mapping
The frontend will directly use the `source_services` array from the API:

- `['office']` - Pure office contact (Google/Microsoft)
- `['email']` - Discovered from email events  
- `['calendar']` - Discovered from calendar events
- `['documents']` - Discovered from document events
- `['office', 'email']` - Office contact also found in email events
- `['email', 'calendar']` - Contact found in multiple event types

### Component File Structure
The new contact system will be organized as:

```
frontend/components/contacts/
├── contact-card.tsx          # Individual contact display
├── contact-filters.tsx       # Filtering and search controls
├── contact-actions.tsx       # Bulk actions and buttons
├── contact-form.tsx          # Create new contact form
├── edit-contact-form.tsx     # Edit existing contact form
├── contact-detail-modal.tsx  # Full contact details
├── discovery-settings.tsx    # Discovery management
├── contact-merger.tsx        # Duplicate merging interface
└── analytics-dashboard.tsx   # Contact analytics
```

### Relevance Scoring
The frontend should leverage the relevance scoring system:
- Sort contacts by relevance score by default
- Show relevance factors (recency, frequency, diversity, name completeness)
- Allow users to adjust relevance weights
- Provide relevance-based recommendations

## Success Criteria
- [ ] Frontend completely uses new Contacts Service data structure
- [ ] All old Office Service contact types and code are removed
- [ ] New contact components provide native bi-source support
- [ ] Users can clearly distinguish between office and discovered contacts
- [ ] All CRUD operations work with new API endpoints
- [ ] Contact discovery is transparent and manageable
- [ ] Performance remains acceptable with large contact lists
- [ ] User experience is intuitive and improves productivity
- [ ] Data consistency is maintained across all operations
- [ ] No legacy contact code remains in the frontend

## Dependencies
- [ ] Contacts Service is fully operational and tested
- [ ] Gateway routing is working correctly (✅ Already completed)
- [ ] Office Service read-through integration is stable
- [ ] Frontend build system supports new dependencies
- [ ] TypeScript compilation passes with new types
- [ ] All old contact types are removed from office API
- [ ] New contact components are created and tested
