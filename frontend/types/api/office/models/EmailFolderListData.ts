/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EmailFolder } from './EmailFolder';
/**
 * Data structure for email folder list responses.
 */
export type EmailFolderListData = {
    folders: Array<EmailFolder>;
    providers_used: Array<string>;
    provider_errors?: (Record<string, string> | null);
    request_metadata: Record<string, any>;
};

