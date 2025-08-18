/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EmailFolder } from './EmailFolder';
import type { Provider } from './Provider';
/**
 * Response model for email folder lists.
 */
export type EmailFolderList = {
    success: boolean;
    data?: (Array<EmailFolder> | null);
    error?: (Record<string, any> | null);
    cache_hit?: boolean;
    provider_used?: (Provider | null);
    request_id: string;
};

