/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { IntegrationProvider } from './IntegrationProvider';
/**
 * Request model for starting OAuth flow.
 */
export type OAuthStartRequest = {
    /**
     * OAuth provider
     */
    provider: IntegrationProvider;
    /**
     * OAuth callback redirect URI (uses default if not provided)
     */
    redirect_uri?: (string | null);
    /**
     * Requested OAuth scopes (uses defaults if not provided)
     */
    scopes?: (Array<string> | null);
    /**
     * Additional state data to preserve through OAuth flow
     */
    state_data?: (Record<string, any> | null);
};

