/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { IntegrationProvider } from './IntegrationProvider';
/**
 * Request model for internal token refresh.
 */
export type InternalTokenRefreshRequest = {
    /**
     * User ID to refresh tokens for
     */
    user_id: string;
    /**
     * OAuth provider
     */
    provider: IntegrationProvider;
    /**
     * Force refresh even if not near expiration
     */
    force?: boolean;
};

