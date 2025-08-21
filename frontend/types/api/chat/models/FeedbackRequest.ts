/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request model for user feedback on messages.
 *
 * Allows users to provide thumbs up/down feedback on AI responses.
 * User ID is extracted from X-User-Id header by the gateway.
 */
export type FeedbackRequest = {
    thread_id: string;
    message_id: string;
    feedback: string;
};

