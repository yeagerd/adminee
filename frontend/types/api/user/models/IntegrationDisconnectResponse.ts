/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { IntegrationProvider } from './IntegrationProvider';
/**
 * Response model for integration disconnection.
 */
export type IntegrationDisconnectResponse = {
    /**
     * Whether disconnection succeeded
     */
    success: boolean;
    /**
     * Integration ID
     */
    integration_id: number;
    /**
     * OAuth provider
     */
    provider: IntegrationProvider;
    /**
     * Whether tokens were revoked
     */
    tokens_revoked: boolean;
    /**
     * Whether associated data was deleted
     */
    data_deleted: boolean;
    /**
     * Disconnection time
     */
    disconnected_at: string;
    /**
     * Error message if failed
     */
    error?: (string | null);
};

