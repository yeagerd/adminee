/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EmailMessage } from './EmailMessage';
import type { Provider } from './Provider';
/**
 * Response model for email message lists.
 */
export type EmailMessageList = {
    success: boolean;
    data?: (Array<EmailMessage> | null);
    error?: (Record<string, any> | null);
    cache_hit?: boolean;
    provider_used?: (Provider | null);
    request_id: string;
};

