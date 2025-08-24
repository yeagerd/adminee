/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request model for chat endpoint.
 *
 * Represents a user's chat message request with optional thread context.
 * User ID is provided via X-User-Id header from the gateway.
 * user_timezone is deprecated; use user_context['timezone'] instead.
 */
export type ChatRequest = {
    thread_id?: (string | null);
    message: string;
    user_context?: (Record<string, any> | null);
    user_timezone?: (string | null);
};

