/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EmailDraftResult } from './EmailDraftResult';
/**
 * Response model for email draft operations.
 */
export type EmailDraftResponse = {
    success: boolean;
    data?: (EmailDraftResult | null);
    error?: (Record<string, any> | null);
    request_id: string;
};

