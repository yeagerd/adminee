/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EmailAddress } from './EmailAddress';
/**
 * Request model for sending emails.
 */
export type SendEmailRequest = {
    to: Array<EmailAddress>;
    subject: string;
    body: string;
    cc?: (Array<EmailAddress> | null);
    bcc?: (Array<EmailAddress> | null);
    reply_to_message_id?: (string | null);
    provider?: (string | null);
    importance?: (string | null);
};

