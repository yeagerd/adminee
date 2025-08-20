/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EmailMessageList } from '../models/EmailMessageList';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class InternalEmailService {
    /**
     * Get Internal Email Messages
     * Internal endpoint for service-to-service communication to get email messages.
     *
     * This endpoint bypasses gateway authentication and uses API key auth.
     * It accepts user_id as a query parameter for direct service calls.
     * @param userId User ID to fetch emails for
     * @param email Email address of the user
     * @param providers Providers to fetch from (google, microsoft). If not specified, fetches from all available providers
     * @param limit Maximum number of messages to return per provider
     * @param includeBody Whether to include message body content
     * @param labels Filter by labels (inbox, sent, etc.)
     * @param folderId Folder ID to fetch messages from (provider-specific)
     * @param q Search query to filter messages
     * @param pageToken Pagination token for next page
     * @param noCache Bypass cache and fetch fresh data from providers
     * @param countOnly Return only count of messages, not the actual messages
     * @returns EmailMessageList Successful Response
     * @throws ApiError
     */
    public static getInternalEmailMessagesInternalMessagesGet(
        userId: string,
        email: string,
        providers?: (Array<string> | null),
        limit: number = 50,
        includeBody: boolean = false,
        labels?: (Array<string> | null),
        folderId?: (string | null),
        q?: (string | null),
        pageToken?: (string | null),
        noCache: boolean = false,
        countOnly: boolean = false,
    ): CancelablePromise<EmailMessageList> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/internal/messages',
            query: {
                'user_id': userId,
                'email': email,
                'providers': providers,
                'limit': limit,
                'include_body': includeBody,
                'labels': labels,
                'folder_id': folderId,
                'q': q,
                'page_token': pageToken,
                'no_cache': noCache,
                'count_only': countOnly,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Internal Email Count
     * Internal endpoint to get email count for service-to-service communication.
     *
     * This endpoint returns only the count of emails, not the actual messages.
     * @param userId User ID to get email count for
     * @param providers Providers to count emails from (google, microsoft). If not specified, counts from all available providers
     * @param labels Filter by labels (inbox, sent, etc.)
     * @param q Search query to filter messages
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getInternalEmailCountInternalMessagesCountGet(
        userId: string,
        providers?: (Array<string> | null),
        labels?: (Array<string> | null),
        q?: (string | null),
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/internal/messages/count',
            query: {
                'user_id': userId,
                'providers': providers,
                'labels': labels,
                'q': q,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
