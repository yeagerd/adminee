/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ContactCreate } from '../models/ContactCreate';
import type { ContactListResponse } from '../models/ContactListResponse';
import type { ContactResponse } from '../models/ContactResponse';
import type { ContactStatsResponse } from '../models/ContactStatsResponse';
import type { EmailContactSearchResult } from '../models/EmailContactSearchResult';
import type { EmailContactUpdate } from '../models/EmailContactUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class InternalService {
    /**
     * List Contacts Internal
     * List contacts for a user with optional filtering (internal service access).
     * @param userId User ID to get contacts for
     * @param limit Maximum number of contacts to return
     * @param offset Number of contacts to skip
     * @param tags Filter by tags
     * @param sourceServices Filter by source services
     * @returns ContactListResponse Successful Response
     * @throws ApiError
     */
    public static listContactsInternalInternalContactsGet(
        userId: string,
        limit: number = 100,
        offset?: number,
        tags?: (Array<string> | null),
        sourceServices?: (Array<string> | null),
    ): CancelablePromise<ContactListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/internal/contacts',
            query: {
                'user_id': userId,
                'limit': limit,
                'offset': offset,
                'tags': tags,
                'source_services': sourceServices,
            },
            errors: {
                401: `Service authentication required`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Contact Internal
     * Create a new contact (internal service access).
     * @param requestBody
     * @returns ContactResponse Successful Response
     * @throws ApiError
     */
    public static createContactInternalInternalContactsPost(
        requestBody: ContactCreate,
    ): CancelablePromise<ContactResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/internal/contacts',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Service authentication required`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Search Contacts Internal
     * Search contacts for a user by query (internal service access).
     * @param userId User ID to search contacts for
     * @param query Search query for name or email
     * @param limit Maximum number of results
     * @param tags Filter by tags
     * @param sourceServices Filter by source services
     * @returns EmailContactSearchResult Successful Response
     * @throws ApiError
     */
    public static searchContactsInternalInternalContactsSearchGet(
        userId: string,
        query: string,
        limit: number = 20,
        tags?: (Array<string> | null),
        sourceServices?: (Array<string> | null),
    ): CancelablePromise<Array<EmailContactSearchResult>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/internal/contacts/search',
            query: {
                'user_id': userId,
                'query': query,
                'limit': limit,
                'tags': tags,
                'source_services': sourceServices,
            },
            errors: {
                401: `Service authentication required`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Contact Stats Internal
     * Get contact statistics for a user (internal service access).
     * @param userId User ID to get stats for
     * @returns ContactStatsResponse Successful Response
     * @throws ApiError
     */
    public static getContactStatsInternalInternalContactsStatsGet(
        userId: string,
    ): CancelablePromise<ContactStatsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/internal/contacts/stats',
            query: {
                'user_id': userId,
            },
            errors: {
                401: `Service authentication required`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Contact Internal
     * Get a specific contact by ID (internal service access).
     * @param contactId Contact ID to retrieve
     * @param userId User ID who owns the contact
     * @returns ContactResponse Successful Response
     * @throws ApiError
     */
    public static getContactInternalInternalContactsContactIdGet(
        contactId: string,
        userId: string,
    ): CancelablePromise<ContactResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/internal/contacts/{contact_id}',
            path: {
                'contact_id': contactId,
            },
            query: {
                'user_id': userId,
            },
            errors: {
                401: `Service authentication required`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Contact Internal
     * Update an existing contact (internal service access).
     * @param contactId Contact ID to update
     * @param userId User ID who owns the contact
     * @param requestBody
     * @returns ContactResponse Successful Response
     * @throws ApiError
     */
    public static updateContactInternalInternalContactsContactIdPut(
        contactId: string,
        userId: string,
        requestBody: EmailContactUpdate,
    ): CancelablePromise<ContactResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/internal/contacts/{contact_id}',
            path: {
                'contact_id': contactId,
            },
            query: {
                'user_id': userId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Service authentication required`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Contact Internal
     * Delete a contact (internal service access).
     * @param contactId Contact ID to delete
     * @param userId User ID who owns the contact
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deleteContactInternalInternalContactsContactIdDelete(
        contactId: string,
        userId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/internal/contacts/{contact_id}',
            path: {
                'contact_id': contactId,
            },
            query: {
                'user_id': userId,
            },
            errors: {
                401: `Service authentication required`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Health Check Internal
     * Health check endpoint for internal service access.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static healthCheckInternalInternalHealthGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/internal/health',
            errors: {
                401: `Service authentication required`,
            },
        });
    }
}
