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
export class ContactsService {
    /**
     * List My Contacts
     * List contacts for the currently authenticated user with optional filtering.
     * @param limit Maximum number of contacts to return
     * @param offset Number of contacts to skip
     * @param tags Filter by tags
     * @param sourceServices Filter by source services
     * @returns ContactListResponse Successful Response
     * @throws ApiError
     */
    public static listMyContactsV1ContactsMeGet(
        limit: number = 100,
        offset?: number,
        tags?: (Array<string> | null),
        sourceServices?: (Array<string> | null),
    ): CancelablePromise<ContactListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/contacts/me',
            query: {
                'limit': limit,
                'offset': offset,
                'tags': tags,
                'source_services': sourceServices,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create My Contact
     * Create a new contact for the currently authenticated user.
     * @param requestBody
     * @returns ContactResponse Successful Response
     * @throws ApiError
     */
    public static createMyContactV1ContactsMePost(
        requestBody: ContactCreate,
    ): CancelablePromise<ContactResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/contacts/me',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Search My Contacts
     * Search contacts for the currently authenticated user by query.
     * @param query Search query for name or email
     * @param limit Maximum number of results
     * @param tags Filter by tags
     * @param sourceServices Filter by source services
     * @returns EmailContactSearchResult Successful Response
     * @throws ApiError
     */
    public static searchMyContactsV1ContactsMeSearchGet(
        query: string,
        limit: number = 20,
        tags?: (Array<string> | null),
        sourceServices?: (Array<string> | null),
    ): CancelablePromise<Array<EmailContactSearchResult>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/contacts/me/search',
            query: {
                'query': query,
                'limit': limit,
                'tags': tags,
                'source_services': sourceServices,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get My Contact Stats
     * Get contact statistics for the currently authenticated user.
     * @returns ContactStatsResponse Successful Response
     * @throws ApiError
     */
    public static getMyContactStatsV1ContactsMeStatsGet(): CancelablePromise<ContactStatsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/contacts/me/stats',
        });
    }
    /**
     * Get My Contact
     * Get a specific contact by ID for the currently authenticated user.
     * @param contactId Contact ID to retrieve
     * @returns ContactResponse Successful Response
     * @throws ApiError
     */
    public static getMyContactV1ContactsMeContactIdGet(
        contactId: string,
    ): CancelablePromise<ContactResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/contacts/me/{contact_id}',
            path: {
                'contact_id': contactId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update My Contact
     * Update an existing contact for the currently authenticated user.
     * @param contactId Contact ID to update
     * @param requestBody
     * @returns ContactResponse Successful Response
     * @throws ApiError
     */
    public static updateMyContactV1ContactsMeContactIdPut(
        contactId: string,
        requestBody: EmailContactUpdate,
    ): CancelablePromise<ContactResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/v1/contacts/me/{contact_id}',
            path: {
                'contact_id': contactId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete My Contact
     * Delete a contact for the currently authenticated user.
     * @param contactId Contact ID to delete
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deleteMyContactV1ContactsMeContactIdDelete(
        contactId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/v1/contacts/me/{contact_id}',
            path: {
                'contact_id': contactId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
