/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Provider } from './Provider';
/**
 * Result data for email send operations.
 */
export type EmailSendResult = {
    message_id: string;
    thread_id?: (string | null);
    provider: Provider;
    sent_at: string;
    recipient_count: number;
    has_attachments?: boolean;
};

