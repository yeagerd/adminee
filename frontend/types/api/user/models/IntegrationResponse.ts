/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { IntegrationProvider } from './IntegrationProvider';
import type { IntegrationStatus } from './IntegrationStatus';
/**
 * Response model for user integration.
 */
export type IntegrationResponse = {
    /**
     * Integration ID
     */
    id: number;
    /**
     * User ID
     */
    user_id: string;
    /**
     * OAuth provider
     */
    provider: IntegrationProvider;
    /**
     * Integration status
     */
    status: IntegrationStatus;
    /**
     * Granted OAuth scopes
     */
    scopes?: Array<string>;
    /**
     * User ID from external provider
     */
    external_user_id?: (string | null);
    /**
     * Email from external provider
     */
    external_email?: (string | null);
    /**
     * Display name from external provider
     */
    external_name?: (string | null);
    /**
     * Whether access token is available
     */
    has_access_token: boolean;
    /**
     * Whether refresh token is available
     */
    has_refresh_token: boolean;
    /**
     * Access token expiration
     */
    token_expires_at?: (string | null);
    /**
     * Token creation time
     */
    token_created_at?: (string | null);
    /**
     * Last successful sync
     */
    last_sync_at?: (string | null);
    /**
     * Last error message if any
     */
    last_error?: (string | null);
    /**
     * Consecutive error count
     */
    error_count?: number;
    /**
     * Integration creation time
     */
    created_at: string;
    /**
     * Last update time
     */
    updated_at: string;
};

