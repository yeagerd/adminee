/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EmailSendResult } from './EmailSendResult';
/**
 * Response model for sending emails.
 */
export type SendEmailResponse = {
    success: boolean;
    data?: (EmailSendResult | null);
    error?: (Record<string, any> | null);
    request_id: string;
};

