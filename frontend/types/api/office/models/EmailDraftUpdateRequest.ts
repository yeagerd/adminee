/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EmailAddress } from './EmailAddress';
/**
 * Request model for updating email drafts in providers.
 */
export type EmailDraftUpdateRequest = {
    to?: (Array<EmailAddress> | null);
    cc?: (Array<EmailAddress> | null);
    bcc?: (Array<EmailAddress> | null);
    subject?: (string | null);
    body?: (string | null);
    provider?: (string | null);
};

