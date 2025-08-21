/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { IntegrationProvider } from './IntegrationProvider';
/**
 * Response model for OAuth scope validation.
 */
export type ScopeValidationResponse = {
    /**
     * OAuth provider
     */
    provider: IntegrationProvider;
    /**
     * Requested scopes
     */
    requested_scopes: Array<string>;
    /**
     * Valid scopes for provider
     */
    valid_scopes: Array<string>;
    /**
     * Invalid scopes
     */
    invalid_scopes?: Array<string>;
    /**
     * Scope validation warnings
     */
    warnings?: Array<string>;
};

