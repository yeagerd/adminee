/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EmailThread } from './EmailThread';
/**
 * Data structure for email thread list responses.
 */
export type EmailThreadListData = {
    threads: Array<EmailThread>;
    total_count: number;
    providers_used: Array<string>;
    provider_errors?: (Record<string, string> | null);
    has_more?: boolean;
    request_metadata: Record<string, any>;
};

