/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ChatRequest } from '../models/ChatRequest';
import type { ChatResponse } from '../models/ChatResponse';
import type { DeleteUserDraftResponse } from '../models/DeleteUserDraftResponse';
import type { FeedbackRequest } from '../models/FeedbackRequest';
import type { FeedbackResponse } from '../models/FeedbackResponse';
import type { UserDraftListResponse } from '../models/UserDraftListResponse';
import type { UserDraftRequest } from '../models/UserDraftRequest';
import type { UserDraftResponse } from '../models/UserDraftResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class DefaultService {
    /**
     * Ready Check
     * @returns any Successful Response
     * @throws ApiError
     */
    public static readyCheckReadyGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/ready',
        });
    }
    /**
     * Chat Endpoint
     * Chat endpoint using WorkflowAgent multi-agent system.
     *
     * Demonstrates database model to API model conversion pattern.
     * @param requestBody
     * @returns ChatResponse Successful Response
     * @throws ApiError
     */
    public static chatEndpointV1ChatCompletionsPost(
        requestBody: ChatRequest,
    ): CancelablePromise<ChatResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/chat/completions',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Chat Stream Endpoint
     * Streaming chat endpoint using Server-Sent Events (SSE).
     *
     * This endpoint streams the multi-agent workflow responses in real-time,
     * allowing clients to see responses as they're generated.
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static chatStreamEndpointV1ChatCompletionsStreamPost(
        requestBody: ChatRequest,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/chat/completions/stream',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Threads
     * List threads for a given user using history_manager.
     *
     * CONVERSION PATTERN EXAMPLE: Thread (database) -> ThreadResponse (API)
     * This function demonstrates the standard pattern for converting database
     * models to API response models.
     * @param limit
     * @param offset
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listThreadsV1ChatThreadsGet(
        limit: number = 20,
        offset?: number,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/chat/threads',
            query: {
                'limit': limit,
                'offset': offset,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Thread History
     * Get chat history for a given thread using history_manager.
     *
     * CONVERSION PATTERN EXAMPLE: Message (database) -> MessageResponse (API)
     * This function demonstrates the standard pattern for converting database
     * models to API response models with computed fields.
     * @param threadId
     * @returns ChatResponse Successful Response
     * @throws ApiError
     */
    public static threadHistoryV1ChatThreadsThreadIdHistoryGet(
        threadId: string,
    ): CancelablePromise<ChatResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/chat/threads/{thread_id}/history',
            path: {
                'thread_id': threadId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Feedback Endpoint
     * Receive user feedback for a message.
     * @param requestBody
     * @returns FeedbackResponse Successful Response
     * @throws ApiError
     */
    public static feedbackEndpointV1ChatFeedbackPost(
        requestBody: FeedbackRequest,
    ): CancelablePromise<FeedbackResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/chat/feedback',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create User Draft Endpoint
     * Create a new user draft.
     * @param requestBody
     * @returns UserDraftResponse Successful Response
     * @throws ApiError
     */
    public static createUserDraftEndpointV1ChatDraftsPost(
        requestBody: UserDraftRequest,
    ): CancelablePromise<UserDraftResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/chat/drafts',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List User Drafts Endpoint
     * List user drafts with optional filtering.
     * @param draftType
     * @param status
     * @param limit
     * @param offset
     * @returns UserDraftListResponse Successful Response
     * @throws ApiError
     */
    public static listUserDraftsEndpointV1ChatDraftsGet(
        draftType?: (string | null),
        status?: (string | null),
        limit: number = 50,
        offset?: number,
    ): CancelablePromise<UserDraftListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/chat/drafts',
            query: {
                'draft_type': draftType,
                'status': status,
                'limit': limit,
                'offset': offset,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get User Draft Endpoint
     * Get a specific user draft.
     * @param draftId
     * @returns UserDraftResponse Successful Response
     * @throws ApiError
     */
    public static getUserDraftEndpointV1ChatDraftsDraftIdGet(
        draftId: string,
    ): CancelablePromise<UserDraftResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/chat/drafts/{draft_id}',
            path: {
                'draft_id': draftId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update User Draft Endpoint
     * Update a user draft.
     * @param draftId
     * @param requestBody
     * @returns UserDraftResponse Successful Response
     * @throws ApiError
     */
    public static updateUserDraftEndpointV1ChatDraftsDraftIdPut(
        draftId: string,
        requestBody: UserDraftRequest,
    ): CancelablePromise<UserDraftResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/v1/chat/drafts/{draft_id}',
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
     * Delete User Draft Endpoint
     * Delete a user draft.
     * @param draftId
     * @returns DeleteUserDraftResponse Successful Response
     * @throws ApiError
     */
    public static deleteUserDraftEndpointV1ChatDraftsDraftIdDelete(
        draftId: string,
    ): CancelablePromise<DeleteUserDraftResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/v1/chat/drafts/{draft_id}',
            path: {
                'draft_id': draftId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Health Check
     * @returns any Successful Response
     * @throws ApiError
     */
    public static healthCheckHealthGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/health',
        });
    }
    /**
     * Health Check
     * @returns any Successful Response
     * @throws ApiError
     */
    public static healthCheckGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/',
        });
    }
}
