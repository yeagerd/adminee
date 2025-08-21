/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { IntegrationProvider } from './IntegrationProvider';
/**
 * Response model for token refresh operation.
 */
export type TokenRefreshResponse = {
    /**
     * Whether token refresh succeeded
     */
    success: boolean;
    /**
     * Integration ID
     */
    integration_id?: (number | null);
    /**
     * OAuth provider
     */
    provider: IntegrationProvider;
    /**
     * New token expiration time
     */
    token_expires_at?: (string | null);
    /**
     * Refresh completion time
     */
    refreshed_at?: (string | null);
    /**
     * Error message if failed
     */
    error?: (string | null);
};

