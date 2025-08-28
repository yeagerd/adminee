# Vespa Search API Types

This directory contains TypeScript interfaces that mirror the Python models in `services/api/v1/vespa/search_models.py` to ensure type safety between frontend and backend.

## Usage Example

```typescript
import { SearchQuery, SearchResponse, SearchResult } from './index';

// Example search function
async function searchUserData(query: string, userId: string): Promise<SearchResponse> {
  const searchQuery: SearchQuery = {
    yql: `select * from briefly_document where user_id = "${userId}" and search_text contains "${query}"`,
    hits: 20,
    ranking: "hybrid",
    timeout: "5.0s",
    streaming_groupname: userId,
  };

  const response = await fetch('/api/v1/vespa/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(searchQuery),
  });

  return response.json();
}

// Example component using search results
function SearchResults({ results }: { results: SearchResult[] }) {
  return (
    <div>
      {results.map((result) => (
        <div key={result.id}>
          <h3>{result.title}</h3>
          <p>Type: {result.source_type}</p>
          <p>Provider: {result.provider}</p>
          <p>Relevance: {result.relevance_score}</p>
          
          {/* Email-specific display */}
          {result.source_type === 'email' && result.sender && (
            <p>From: {result.sender}</p>
          )}
          
          {/* Calendar-specific display */}
          {result.source_type === 'calendar' && result.start_time && (
            <p>Start: {new Date(result.start_time * 1000).toLocaleString()}</p>
          )}
        </div>
      ))}
    </div>
  );
}
```

## Type Safety Benefits

1. **Consistent Data Structure**: Frontend and backend use the same data models
2. **IntelliSense**: Full autocomplete and type checking in your IDE
3. **Runtime Validation**: Pydantic models ensure data integrity on the backend
4. **API Evolution**: Changes to models are reflected in both frontend and backend

## Model Relationships

- `SearchQuery` → Input for search operations
- `SearchResponse` → Complete search response containing results
- `SearchResult` → Individual document/result with type-specific fields
- `SearchFacets` → Aggregated counts by various dimensions
- `SearchPerformance` → Search execution metrics
- `SearchError` → Error responses with structured error information
- `SearchSummary` → High-level summary of search results

## Field Mapping

The `SearchResult` interface includes fields for different document types:

- **Email**: `sender`, `recipients`, `thread_id`, `folder`, `quoted_content`
- **Calendar**: `start_time`, `end_time`, `attendees`, `location`, `is_all_day`
- **Contact**: `display_name`, `email_addresses`, `company`, `job_title`
- **Document**: `file_name`, `file_size`, `mime_type`

All types share common fields like `id`, `user_id`, `source_type`, `provider`, etc.
