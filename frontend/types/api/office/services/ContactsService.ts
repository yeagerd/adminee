/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { _ContactCreatePayload } from '../models/_ContactCreatePayload';
import type { _ContactUpdatePayload } from '../models/_ContactUpdatePayload';
import type { ContactList } from '../models/ContactList';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ContactsService {
    /**
     * List Contacts
     * @param providers Providers to fetch from (google, microsoft).
     * @param limit
     * @param q Free-text search (name or email)
     * @param company Filter by company or email domain
     * @param noCache Bypass cache and fetch fresh data from providers
     * @returns ContactList Successful Response
     * @throws ApiError
     */
    public static listContactsV1ContactsGet(
        providers?: (Array<string> | null),
        limit: number = 100,
        q?: (string | null),
        company?: (string | null),
        noCache: boolean = false,
    ): CancelablePromise<ContactList> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/contacts/',
            query: {
                'providers': providers,
                'limit': limit,
                'q': q,
                'company': company,
                'no_cache': noCache,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Contact
     * @param provider Provider to create contact in (google, microsoft) - optional if provided in JSON body
     * @param fullName
     * @param givenName
     * @param familyName
     * @param emails
     * @param company
     * @param jobTitle
     * @param phones
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createContactV1ContactsPost(
        provider?: (string | null),
        fullName?: (string | null),
        givenName?: (string | null),
        familyName?: (string | null),
        emails?: (Array<string> | null),
        company?: (string | null),
        jobTitle?: (string | null),
        phones?: (Array<string> | null),
        requestBody?: (_ContactCreatePayload | null),
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/contacts/',
            query: {
                'provider': provider,
                'full_name': fullName,
                'given_name': givenName,
                'family_name': familyName,
                'emails': emails,
                'company': company,
                'job_title': jobTitle,
                'phones': phones,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Contact
     * @param contactId Unified contact id (provider_originalId) or provider id for write-through
     * @param provider Provider to update in (if unified id not used) - optional if provided in JSON body
     * @param fullName
     * @param givenName
     * @param familyName
     * @param company
     * @param jobTitle
     * @param emails
     * @param phones
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static updateContactV1ContactsContactIdPut(
        contactId: string,
        provider?: (string | null),
        fullName?: (string | null),
        givenName?: (string | null),
        familyName?: (string | null),
        company?: (string | null),
        jobTitle?: (string | null),
        emails?: (Array<string> | null),
        phones?: (Array<string> | null),
        requestBody?: (_ContactUpdatePayload | null),
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/v1/contacts/{contact_id}',
            path: {
                'contact_id': contactId,
            },
            query: {
                'provider': provider,
                'full_name': fullName,
                'given_name': givenName,
                'family_name': familyName,
                'company': company,
                'job_title': jobTitle,
                'emails': emails,
                'phones': phones,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Contact
     * @param contactId
     * @param provider Provider to delete in (if unified id not used)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deleteContactV1ContactsContactIdDelete(
        contactId: string,
        provider?: (string | null),
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/v1/contacts/{contact_id}',
            path: {
                'contact_id': contactId,
            },
            query: {
                'provider': provider,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
