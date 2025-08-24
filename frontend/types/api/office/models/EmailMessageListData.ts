/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EmailMessage } from './EmailMessage';
/**
 * Data structure for email message list responses.
 */
export type EmailMessageListData = {
    messages: Array<EmailMessage>;
    total_count: number;
    providers_used: Array<string>;
    provider_errors?: (Record<string, string> | null);
    has_more?: boolean;
    request_metadata: Record<string, any>;
};

