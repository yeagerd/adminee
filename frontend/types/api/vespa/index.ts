/**
 * Vespa search API types.
 * 
 * These types mirror the Python models in services/api/v1/vespa/search_models.py
 * to ensure type safety between frontend and backend.
 */

export interface SearchQuery {
  yql: string;
  hits?: number;
  ranking?: string;
  timeout?: string;
  streaming_groupname?: string;
  offset?: number;
  query_profile?: string;
  trace_level?: number;
}

export interface SearchResult {
  id: string;
  user_id: string;
  source_type: string;
  provider: string;
  title: string;
  content: string;
  search_text: string;
  created_at?: number;
  updated_at?: number;
  relevance_score: number;
  
  // Email-specific fields
  sender?: string;
  recipients: string[];
  thread_id?: string;
  folder?: string;
  quoted_content?: string;
  thread_summary?: Record<string, any>;
  
  // Calendar-specific fields
  start_time?: number;
  end_time?: number;
  attendees: string[];
  location?: string;
  is_all_day?: boolean;
  recurring?: boolean;
  
  // Contact-specific fields
  display_name?: string;
  email_addresses: string[];
  company?: string;
  job_title?: string;
  phone_numbers: string[];
  address?: string;
  
  // Document-specific fields
  file_name?: string;
  file_size?: number;
  mime_type?: string;
  
  // Metadata
  metadata: Record<string, any>;
  
  // Search-specific fields
  highlights: string[];
  snippet?: string;
  search_method?: string;
  match_confidence?: string;
  vector_similarity?: number;
  keyword_matches?: Record<string, any>;
}

export interface SearchFacets {
  source_types: Record<string, number>;
  providers: Record<string, number>;
  folders: Record<string, number>;
  date_ranges: Record<string, number>;
}

export interface SearchPerformance {
  query_time_ms: number;
  total_time_ms: number;
  search_time_ms: number;
  match_time_ms: number;
  fetch_time_ms: number;
}

export interface SearchResponse {
  query: string;
  user_id: string;
  total_hits: number;
  documents: SearchResult[];
  facets: SearchFacets;
  performance: SearchPerformance;
  coverage?: Record<string, any>;
  processed_at: string;
}

export interface SearchError {
  query: string;
  user_id: string;
  error: string;
  error_code?: string;
  details?: Record<string, any>;
  processed_at: string;
}

export interface SearchSummary {
  total_results: number;
  result_types: Record<string, number>;
  top_results: SearchResult[];
  query_analysis?: Record<string, any>;
}

// Re-export all types
export type {
  SearchQuery,
  SearchResult,
  SearchFacets,
  SearchPerformance,
  SearchResponse,
  SearchError,
  SearchSummary,
};
