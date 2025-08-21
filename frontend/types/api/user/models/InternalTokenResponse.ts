/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { IntegrationProvider } from './IntegrationProvider';
/**
 * Response model for internal token retrieval.
 */
export type InternalTokenResponse = {
    /**
     * Whether token retrieval succeeded
     */
    success: boolean;
    /**
     * OAuth access token
     */
    access_token?: (string | null);
    /**
     * OAuth refresh token
     */
    refresh_token?: (string | null);
    /**
     * Token expiration time
     */
    expires_at?: (string | null);
    /**
     * Granted scopes
     */
    scopes?: Array<string>;
    /**
     * OAuth provider
     */
    provider: IntegrationProvider;
    /**
     * User ID
     */
    user_id: string;
    /**
     * Integration ID
     */
    integration_id?: (number | null);
    /**
     * Token type
     */
    token_type?: string;
    /**
     * Error message if failed
     */
    error?: (string | null);
};

