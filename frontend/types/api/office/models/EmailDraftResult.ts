/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Provider } from './Provider';
/**
 * Result data for email draft operations.
 */
export type EmailDraftResult = {
    draft_id: string;
    thread_id?: (string | null);
    provider: Provider;
    created_at: string;
    updated_at?: (string | null);
    action: string;
};

