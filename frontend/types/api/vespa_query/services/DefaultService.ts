/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class DefaultService {
    /**
     * Health Check
     * Health check endpoint
     * @returns string Successful Response
     * @throws ApiError
     */
    public static healthCheckHealthGet(): CancelablePromise<Record<string, string>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/health',
        });
    }
    /**
     * Root
     * Root endpoint
     * @returns string Successful Response
     * @throws ApiError
     */
    public static rootGet(): CancelablePromise<Record<string, string>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/',
        });
    }
    /**
     * Search
     * Execute a search query
     * @param query Search query
     * @param userId User ID
     * @param maxHits Maximum number of results
     * @param offset Result offset
     * @param sourceTypes Filter by source types
     * @param providers Filter by providers
     * @param dateFrom Start date for filtering
     * @param dateTo End date for filtering
     * @param folders Filter by folders
     * @param includeFacets Include facets in results
     * @returns any Successful Response
     * @throws ApiError
     */
    public static searchSearchPost(
        query: string,
        userId: string,
        maxHits: number = 10,
        offset?: number,
        sourceTypes?: (Array<string> | null),
        providers?: (Array<string> | null),
        dateFrom?: (string | null),
        dateTo?: (string | null),
        folders?: (Array<string> | null),
        includeFacets: boolean = true,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/search',
            query: {
                'query': query,
                'user_id': userId,
                'max_hits': maxHits,
                'offset': offset,
                'source_types': sourceTypes,
                'providers': providers,
                'date_from': dateFrom,
                'date_to': dateTo,
                'folders': folders,
                'include_facets': includeFacets,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Autocomplete
     * Get autocomplete suggestions
     * @param query Autocomplete query
     * @param userId User ID
     * @param maxSuggestions Maximum number of suggestions
     * @returns any Successful Response
     * @throws ApiError
     */
    public static autocompleteAutocompletePost(
        query: string,
        userId: string,
        maxSuggestions: number = 5,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/autocomplete',
            query: {
                'query': query,
                'user_id': userId,
                'max_suggestions': maxSuggestions,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Find Similar
     * Find similar documents
     * @param documentId Document ID to find similar documents for
     * @param userId User ID
     * @param maxHits Maximum number of similar documents
     * @returns any Successful Response
     * @throws ApiError
     */
    public static findSimilarSimilarPost(
        documentId: string,
        userId: string,
        maxHits: number = 10,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/similar',
            query: {
                'document_id': documentId,
                'user_id': userId,
                'max_hits': maxHits,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Facets
     * Get facet information
     * @param userId User ID
     * @param sourceTypes Filter by source types
     * @param providers Filter by providers
     * @param dateFrom Start date for filtering
     * @param dateTo End date for filtering
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getFacetsFacetsPost(
        userId: string,
        sourceTypes?: (Array<string> | null),
        providers?: (Array<string> | null),
        dateFrom?: (string | null),
        dateTo?: (string | null),
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/facets',
            query: {
                'user_id': userId,
                'source_types': sourceTypes,
                'providers': providers,
                'date_from': dateFrom,
                'date_to': dateTo,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Trending
     * Get trending documents
     * @param userId User ID
     * @param timeRange Time range for trending
     * @param maxHits Maximum number of trending documents
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getTrendingTrendingPost(
        userId: string,
        timeRange: string = '7d',
        maxHits: number = 10,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/trending',
            query: {
                'user_id': userId,
                'time_range': timeRange,
                'max_hits': maxHits,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Analytics
     * Get analytics data
     * @param userId User ID
     * @param timeRange Time range for analytics
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getAnalyticsAnalyticsPost(
        userId: string,
        timeRange: string = '30d',
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/analytics',
            query: {
                'user_id': userId,
                'time_range': timeRange,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
