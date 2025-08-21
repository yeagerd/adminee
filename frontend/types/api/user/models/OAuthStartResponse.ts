/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { IntegrationProvider } from './IntegrationProvider';
/**
 * Response model for OAuth flow initiation.
 */
export type OAuthStartResponse = {
    /**
     * OAuth provider
     */
    provider: IntegrationProvider;
    /**
     * OAuth authorization URL
     */
    authorization_url: string;
    /**
     * OAuth state parameter
     */
    state: string;
    /**
     * State expiration time
     */
    expires_at: string;
    /**
     * Scopes that will be requested
     */
    requested_scopes?: Array<string>;
};

