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
     * Ingest Document
     * Ingest a document into Vespa
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static ingestDocumentIngestPost(
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/ingest',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Ingest Batch Documents
     * Ingest multiple documents in batch
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static ingestBatchDocumentsIngestBatchPost(
        requestBody: Array<Record<string, any>>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/ingest/batch',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Document
     * Delete a document from Vespa
     * @param userId
     * @param documentId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deleteDocumentDocumentUserIdDocumentIdDelete(
        userId: string,
        documentId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/document/{user_id}/{document_id}',
            path: {
                'user_id': userId,
                'document_id': documentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Document
     * Get a document from Vespa
     * @param userId
     * @param documentId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getDocumentDocumentUserIdDocumentIdGet(
        userId: string,
        documentId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/document/{user_id}/{document_id}',
            path: {
                'user_id': userId,
                'document_id': documentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Search Documents
     * Search documents for a user
     * @param userId
     * @param query
     * @param limit
     * @returns any Successful Response
     * @throws ApiError
     */
    public static searchDocumentsSearchUserIdGet(
        userId: string,
        query: string = '',
        limit: number = 10,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/search/{user_id}',
            path: {
                'user_id': userId,
            },
            query: {
                'query': query,
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get User Stats
     * Get statistics for a user
     * @param userId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getUserStatsStatsUserIdGet(
        userId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/stats/{user_id}',
            path: {
                'user_id': userId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Debug Pubsub Status
     * Debug endpoint to check Pub/Sub consumer status
     * @returns any Successful Response
     * @throws ApiError
     */
    public static debugPubsubStatusDebugPubsubGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/debug/pubsub',
        });
    }
    /**
     * Debug Trigger Pubsub Processing
     * Debug endpoint to manually trigger Pub/Sub message processing
     * @returns any Successful Response
     * @throws ApiError
     */
    public static debugTriggerPubsubProcessingDebugPubsubTriggerPost(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/debug/pubsub/trigger',
        });
    }
    /**
     * Debug Vespa Status
     * Debug endpoint to check Vespa connection and stats
     * @returns any Successful Response
     * @throws ApiError
     */
    public static debugVespaStatusDebugVespaGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/debug/vespa',
        });
    }
}
