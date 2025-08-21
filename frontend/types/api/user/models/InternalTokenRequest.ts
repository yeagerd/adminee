/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { IntegrationProvider } from './IntegrationProvider';
/**
 * Request model for internal token retrieval.
 */
export type InternalTokenRequest = {
    /**
     * User ID to retrieve tokens for
     */
    user_id: string;
    /**
     * OAuth provider
     */
    provider: IntegrationProvider;
    /**
     * Required OAuth scopes
     */
    required_scopes?: Array<string>;
    /**
     * Automatically refresh if token is near expiration
     */
    refresh_if_needed?: boolean;
};

