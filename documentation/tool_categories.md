# Tool Categories Reference

This document provides a comprehensive reference for all tool categories in the Briefly platform's tool discovery system.

## Overview

Tools are organized into logical categories to help agents and developers understand their purpose and find the right tool for specific tasks. Each category serves a distinct function within the overall system architecture.

## Category Details

### 1. Data Retrieval (`data_retrieval`)

**Purpose**: Access user data from various integrated services

**Security**: All data retrieval tools require authentication and are pre-bound with user context to prevent unauthorized access.

**Service Dependencies**: 
- Office Service (calendar, email, documents, notes)

**Available Tools**:

#### `get_calendar_events`
- **Description**: Retrieve calendar events for a user from the office service
- **Parameters**:
  - `start_date` (optional): Start date in YYYY-MM-DD format
  - `end_date` (optional): End date in YYYY-MM-DD format
  - `time_zone` (optional): Timezone for date filtering (default: UTC)
  - `providers` (optional): List of calendar providers to query
  - `limit` (optional): Maximum number of events to return (default: 50)
- **Use Cases**: Meeting scheduling, calendar analysis, availability checking

#### `get_emails`
- **Description**: Get emails from the office service
- **Parameters**:
  - `start_date` (optional): Start date in YYYY-MM-DD format
  - `end_date` (optional): End date in YYYY-MM-DD format
  - `folder` (optional): Folder to filter by
  - `unread_only` (optional): Whether to return only unread emails
  - `search_query` (optional): Search query to filter emails
  - `max_results` (optional): Maximum number of results to return
- **Use Cases**: Email analysis, conversation threading, priority detection

#### `get_notes`
- **Description**: Get notes from the office service
- **Parameters**:
  - `notebook` (optional): Notebook to filter by
  - `tags` (optional): Tags to filter by
  - `search_query` (optional): Search query to filter notes
  - `max_results` (optional): Maximum number of results to return
- **Use Cases**: Knowledge retrieval, note-taking assistance, information lookup

#### `get_documents`
- **Description**: Get documents from the office service
- **Parameters**:
  - `document_type` (optional): Type of document to filter by
  - `start_date` (optional): Start date in YYYY-MM-DD format
  - `end_date` (optional): End date in YYYY-MM-DD format
  - `search_query` (optional): Search query to filter documents
  - `max_results` (optional): Maximum number of results to return
- **Use Cases**: Document discovery, content analysis, file management

---

### 2. Draft Management (`draft_management`)

**Purpose**: Create, update, and manage draft content for emails and calendar events

**Security**: Requires authentication, operates within user's thread context

**Service Dependencies**: None (in-memory draft storage)

**Available Tools**:

#### `create_draft_email`
- **Description**: Create or update an email draft for the current thread
- **Parameters**:
  - `thread_id` (required): Thread ID for the draft
  - `to` (optional): Recipient email address
  - `subject` (optional): Email subject
  - `body` (optional): Email body content
- **Use Cases**: Email composition, response drafting, email templates

#### `create_draft_calendar_event`
- **Description**: Create or update a calendar event draft for the current thread
- **Parameters**:
  - `thread_id` (required): Thread ID for the draft
  - `title` (optional): Event title
  - `start_time` (optional): Start time (ISO format)
  - `end_time` (optional): End time (ISO format)
  - `attendees` (optional): Comma-separated attendee emails
  - `location` (optional): Event location
  - `description` (optional): Event description
- **Use Cases**: Meeting scheduling, event planning, calendar management

#### `create_draft_calendar_change`
- **Description**: Create a draft for changing an existing calendar event
- **Parameters**:
  - `thread_id` (required): Thread ID for the draft
  - `event_id` (optional): ID of the event to change
  - `changes` (optional): JSON string of changes to make
- **Use Cases**: Meeting rescheduling, event updates, calendar modifications

#### Draft Deletion Tools
- `delete_draft_email`: Remove email drafts
- `delete_draft_calendar_event`: Remove calendar event drafts  
- `delete_draft_calendar_edit`: Remove calendar edit drafts
- `clear_all_drafts`: Remove all drafts for a thread

---

### 3. Search (`search`)

**Purpose**: Search and discover information across various data sources

**Security**: Mixed - some tools require user authentication, others are general purpose

**Service Dependencies**: Vespa search engine, various data sources

**Available Tools**:

#### `semantic_search`
- **Description**: Perform semantic search across user data using advanced NLP
- **Parameters**:
  - `query` (required): Search query string
  - `max_results` (optional): Maximum number of results (default: 10)
  - `filters` (optional): Additional search filters
- **Use Cases**: Intelligent content discovery, context-aware search, knowledge retrieval

#### `user_data_search`
- **Description**: Search specifically within user's personal data
- **Parameters**:
  - `query` (required): Search query string
  - `data_types` (optional): Types of data to search (emails, notes, documents)
  - `max_results` (optional): Maximum number of results
- **Use Cases**: Personal information lookup, cross-platform search, unified data access

#### `vespa_search`
- **Description**: Advanced search using Vespa search engine capabilities
- **Parameters**:
  - `query` (required): Vespa query string
  - `ranking` (optional): Ranking profile to use
  - `filters` (optional): Search filters and constraints
- **Use Cases**: Advanced search scenarios, custom ranking, complex queries

---

### 4. Web Search (`web_search`)

**Purpose**: Search external web sources for information

**Security**: No authentication required

**Service Dependencies**: External web search APIs

**Available Tools**:

#### `web_search`
- **Description**: Search the web for information using external APIs
- **Parameters**:
  - `query` (required): Search query string
  - `max_results` (optional): Maximum number of results (default: 5)
  - `search_type` (optional): Type of search (web, news, images)
- **Use Cases**: External information lookup, current events, fact checking

---

### 5. Utility (`utility`)

**Purpose**: Helper functions for data processing, validation, and formatting

**Security**: Generally no authentication required (pure functions)

**Service Dependencies**: None (local processing)

**Available Tools**:

#### Text Processing
- `sanitize_string`: Clean and sanitize text strings
- `generate_summary`: Generate text summaries
- `extract_phone_number`: Extract phone numbers from text

#### Validation
- `validate_email_format`: Validate email address format

#### Date/Time Processing  
- `parse_date_range`: Parse date range strings
- `format_event_time_for_display`: Format event times for display

#### File Operations
- `format_file_size`: Format file sizes for human-readable display

---

## Category Selection Guidelines

When choosing tools for specific tasks:

### For Data Access
- Use **Data Retrieval** tools when you need user's personal data
- Ensure proper authentication and user context
- Consider data source and format requirements

### For Content Creation
- Use **Draft Management** tools when creating content that users will review/send later
- Always work within the appropriate thread context
- Provide clear preview of what will be created

### For Information Discovery
- Use **Search** tools for finding existing information
- Use **Web Search** for external/current information
- Consider search scope and result relevance

### For Data Processing
- Use **Utility** tools for formatting, validation, and transformation
- These are typically safe, stateless operations
- Good for data preparation and presentation

## Adding New Categories

When the system grows and new categories are needed:

1. **Evaluate Existing Categories**: Ensure the new category truly represents a distinct functional area
2. **Define Category Purpose**: Write a clear purpose statement and use cases
3. **Consider Security Requirements**: Determine authentication and authorization needs
4. **Plan Service Dependencies**: Identify what external services or resources are needed
5. **Update Documentation**: Add the new category to this reference document
6. **Create Examples**: Provide sample tools and usage patterns

## Best Practices

1. **Choose the Right Category**: Select the category that best matches the tool's primary function
2. **Follow Security Patterns**: Use appropriate authentication patterns for each category
3. **Maintain Consistency**: Follow naming and parameter conventions within categories
4. **Document Dependencies**: Clearly specify service dependencies and requirements
5. **Test Across Categories**: Ensure tools work well together across category boundaries
