/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { IntegrationProvider } from './IntegrationProvider';
/**
 * Response model for internal user status retrieval.
 */
export type InternalUserStatusResponse = {
    /**
     * User ID
     */
    user_id: string;
    /**
     * Number of active integrations
     */
    active_integrations: number;
    /**
     * Total number of integrations
     */
    total_integrations: number;
    /**
     * Available providers
     */
    providers?: Array<IntegrationProvider>;
    /**
     * Whether any integrations have errors
     */
    has_errors: boolean;
    /**
     * Last successful sync across all integrations
     */
    last_sync_at?: (string | null);
};

