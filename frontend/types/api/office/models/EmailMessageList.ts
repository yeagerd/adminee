/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EmailMessageListData } from './EmailMessageListData';
import type { Provider } from './Provider';
/**
 * Response model for email message lists.
 */
export type EmailMessageList = {
    success: boolean;
    data?: (EmailMessageListData | null);
    error?: (Record<string, any> | null);
    cache_hit?: boolean;
    provider_used?: (Provider | null);
    request_id: string;
};

