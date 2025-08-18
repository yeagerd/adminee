/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EmailThread } from './EmailThread';
import type { Provider } from './Provider';
/**
 * Response model for email thread lists.
 */
export type EmailThreadList = {
    success: boolean;
    data?: (Array<EmailThread> | null);
    error?: (Record<string, any> | null);
    cache_hit?: boolean;
    provider_used?: (Provider | null);
    request_id: string;
};

