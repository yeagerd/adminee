/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { IntegrationProvider } from './IntegrationProvider';
import type { IntegrationStatus } from './IntegrationStatus';
/**
 * Response model for OAuth callback completion.
 */
export type OAuthCallbackResponse = {
    /**
     * Whether OAuth flow completed successfully
     */
    success: boolean;
    /**
     * Created/updated integration ID
     */
    integration_id?: (number | null);
    /**
     * OAuth provider
     */
    provider: IntegrationProvider;
    /**
     * Integration status
     */
    status: IntegrationStatus;
    /**
     * Granted scopes
     */
    scopes?: Array<string>;
    /**
     * User info from external provider
     */
    external_user_info?: (Record<string, any> | null);
    /**
     * Error message if failed
     */
    error?: (string | null);
};

