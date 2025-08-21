/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MessageResponse } from './MessageResponse';
/**
 * Response model for chat endpoint.
 *
 * Contains the complete chat response including thread context and messages.
 * Uses MessageResponse models for consistent API serialization.
 */
export type ChatResponse = {
    thread_id: string;
    messages: Array<MessageResponse>;
    drafts?: null;
};

