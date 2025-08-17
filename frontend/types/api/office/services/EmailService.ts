/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EmailDraftCreateRequest } from '../models/EmailDraftCreateRequest';
import type { EmailDraftResponse } from '../models/EmailDraftResponse';
import type { EmailDraftUpdateRequest } from '../models/EmailDraftUpdateRequest';
import type { EmailFolderList } from '../models/EmailFolderList';
import type { EmailMessageList } from '../models/EmailMessageList';
import type { EmailThreadList } from '../models/EmailThreadList';
import type { SendEmailRequest } from '../models/SendEmailRequest';
import type { SendEmailResponse } from '../models/SendEmailResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class EmailService {
    /**
     * Get Email Messages
     * Get unified email messages from multiple providers.
     *
     * Fetches email messages from Google Gmail and Microsoft Outlook APIs,
     * normalizes them to a unified format, and returns aggregated results.
     * Responses are cached for improved performance.
     *
     * Args:
     * user_id: ID of the user to fetch emails for
     * providers: List of providers to query (defaults to all available)
     * limit: Maximum messages per provider
     * include_body: Whether to include full message bodies
     * labels: Filter by message labels/categories
     * q: Search query string
     * page_token: Pagination token
     *
     * Returns:
     * EmailMessageList with aggregated email messages
     * @param providers Providers to fetch from (google, microsoft). If not specified, fetches from all available providers
     * @param limit Maximum number of messages to return per provider
     * @param includeBody Whether to include message body content
     * @param labels Filter by labels (inbox, sent, etc.)
     * @param folderId Folder ID to fetch messages from (provider-specific)
     * @param q Search query to filter messages
     * @param pageToken Pagination token for next page
     * @param noCache Bypass cache and fetch fresh data from providers
     * @returns EmailMessageList Successful Response
     * @throws ApiError
     */
    public static getEmailMessagesV1EmailMessagesGet(
        providers?: (Array<string> | null),
        limit: number = 50,
        includeBody: boolean = false,
        labels?: (Array<string> | null),
        folderId?: (string | null),
        q?: (string | null),
        pageToken?: (string | null),
        noCache: boolean = false,
    ): CancelablePromise<EmailMessageList> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/email/messages',
            query: {
                'providers': providers,
                'limit': limit,
                'include_body': includeBody,
                'labels': labels,
                'folder_id': folderId,
                'q': q,
                'page_token': pageToken,
                'no_cache': noCache,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Email Folders
     * Get unified email folders/labels from multiple providers.
     *
     * Fetches email folders from Microsoft Outlook and labels from Google Gmail APIs,
     * normalizes them to a unified format, and returns aggregated results.
     * Responses are cached for improved performance.
     *
     * Args:
     * user_id: ID of the user to fetch folders for
     * providers: List of providers to query (defaults to all available)
     * no_cache: Bypass cache and fetch fresh data
     *
     * Returns:
     * EmailFolderList with aggregated email folders
     * @param providers Providers to fetch from (google, microsoft). If not specified, fetches from all available providers
     * @param noCache Bypass cache and fetch fresh data from providers
     * @returns EmailFolderList Successful Response
     * @throws ApiError
     */
    public static getEmailFoldersV1EmailFoldersGet(
        providers?: (Array<string> | null),
        noCache: boolean = false,
    ): CancelablePromise<EmailFolderList> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/email/folders',
            query: {
                'providers': providers,
                'no_cache': noCache,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Email Message
     * Get a specific email message by ID.
     *
     * The message_id should be in the format "provider_originalId" (e.g., "gmail_abc123" or "outlook_xyz789").
     * This endpoint determines the correct provider from the message ID and fetches the full message details.
     *
     * Args:
     * message_id: Message ID with provider prefix
     * user_id: ID of the user who owns the message
     * include_body: Whether to include full message body
     *
     * Returns:
     * EmailMessageList with the specific email message
     * @param messageId Message ID (format: provider_originalId)
     * @param includeBody Whether to include message body content
     * @returns EmailMessageList Successful Response
     * @throws ApiError
     */
    public static getEmailMessageV1EmailMessagesMessageIdGet(
        messageId: string,
        includeBody: boolean = true,
    ): CancelablePromise<EmailMessageList> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/email/messages/{message_id}',
            path: {
                'message_id': messageId,
            },
            query: {
                'include_body': includeBody,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Send Email
     * Send an email message.
     *
     * This endpoint supports sending emails through Gmail and Outlook.
     * The provider can be specified in the request, otherwise it uses the user's default preference.
     * @param requestBody
     * @returns SendEmailResponse Successful Response
     * @throws ApiError
     */
    public static sendEmailV1EmailSendPost(
        requestBody: SendEmailRequest,
    ): CancelablePromise<SendEmailResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/email/send',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Email Threads
     * Get email threads from multiple providers.
     *
     * This endpoint fetches email threads from Gmail and/or Outlook,
     * normalizes them to a unified format, and returns them grouped by thread.
     * @param providers Providers to fetch from (google, microsoft). If not specified, fetches from all available providers
     * @param limit Maximum number of threads to return per provider
     * @param includeBody Whether to include message body content
     * @param labels Filter by labels (inbox, sent, etc.)
     * @param folderId Folder ID to fetch threads from (provider-specific)
     * @param q Search query to filter threads
     * @param pageToken Pagination token for next page
     * @param noCache Bypass cache and fetch fresh data from providers
     * @returns EmailThreadList Successful Response
     * @throws ApiError
     */
    public static getEmailThreadsV1EmailThreadsGet(
        providers?: (Array<string> | null),
        limit: number = 50,
        includeBody: boolean = false,
        labels?: (Array<string> | null),
        folderId?: (string | null),
        q?: (string | null),
        pageToken?: (string | null),
        noCache: boolean = false,
    ): CancelablePromise<EmailThreadList> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/email/threads',
            query: {
                'providers': providers,
                'limit': limit,
                'include_body': includeBody,
                'labels': labels,
                'folder_id': folderId,
                'q': q,
                'page_token': pageToken,
                'no_cache': noCache,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Email Thread
     * Get a specific email thread with all its messages.
     *
     * This endpoint fetches a specific thread and all its messages from the provider.
     * @param threadId Thread ID (format: provider_originalId)
     * @param includeBody Whether to include message body content
     * @param noCache Bypass cache and fetch fresh data from providers
     * @returns EmailThreadList Successful Response
     * @throws ApiError
     */
    public static getEmailThreadV1EmailThreadsThreadIdGet(
        threadId: string,
        includeBody: boolean = true,
        noCache: boolean = false,
    ): CancelablePromise<EmailThreadList> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/email/threads/{thread_id}',
            path: {
                'thread_id': threadId,
            },
            query: {
                'include_body': includeBody,
                'no_cache': noCache,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Message Thread
     * Get the thread containing a specific message.
     *
     * This endpoint finds the thread that contains the specified message and returns all messages in that thread.
     * @param messageId Message ID (format: provider_originalId)
     * @param includeBody Whether to include message body content
     * @param noCache Bypass cache and fetch fresh data from providers
     * @returns EmailThreadList Successful Response
     * @throws ApiError
     */
    public static getMessageThreadV1EmailMessagesMessageIdThreadGet(
        messageId: string,
        includeBody: boolean = true,
        noCache: boolean = false,
    ): CancelablePromise<EmailThreadList> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/email/messages/{message_id}/thread',
            path: {
                'message_id': messageId,
            },
            query: {
                'include_body': includeBody,
                'no_cache': noCache,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Email Draft
     * Create an email draft in the provider (Gmail or Outlook).
     * @param requestBody
     * @returns EmailDraftResponse Successful Response
     * @throws ApiError
     */
    public static createEmailDraftV1EmailDraftsPost(
        requestBody: EmailDraftCreateRequest,
    ): CancelablePromise<EmailDraftResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/email/drafts',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Email Draft
     * @param draftId
     * @param requestBody
     * @returns EmailDraftResponse Successful Response
     * @throws ApiError
     */
    public static updateEmailDraftV1EmailDraftsDraftIdPut(
        draftId: string,
        requestBody: EmailDraftUpdateRequest,
    ): CancelablePromise<EmailDraftResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/v1/email/drafts/{draft_id}',
            path: {
                'draft_id': draftId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Email Draft
     * @param draftId
     * @param provider
     * @returns EmailDraftResponse Successful Response
     * @throws ApiError
     */
    public static deleteEmailDraftV1EmailDraftsDraftIdDelete(
        draftId: string,
        provider: string,
    ): CancelablePromise<EmailDraftResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/v1/email/drafts/{draft_id}',
            path: {
                'draft_id': draftId,
            },
            query: {
                'provider': provider,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Thread Drafts
     * List provider drafts associated with a unified thread id.
     * @param threadId
     * @returns EmailDraftResponse Successful Response
     * @throws ApiError
     */
    public static listThreadDraftsV1EmailThreadsThreadIdDraftsGet(
        threadId: string,
    ): CancelablePromise<EmailDraftResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/email/threads/{thread_id}/drafts',
            path: {
                'thread_id': threadId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
