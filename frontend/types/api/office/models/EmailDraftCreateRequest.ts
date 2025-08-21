/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EmailAddress } from './EmailAddress';
/**
 * Request model for creating email drafts in providers (Google/Microsoft).
 */
export type EmailDraftCreateRequest = {
    /**
     * Draft action: new, reply, reply_all, forward
     */
    action?: string;
    to?: (Array<EmailAddress> | null);
    cc?: (Array<EmailAddress> | null);
    bcc?: (Array<EmailAddress> | null);
    subject?: (string | null);
    body?: (string | null);
    thread_id?: (string | null);
    reply_to_message_id?: (string | null);
    provider?: (string | null);
};

