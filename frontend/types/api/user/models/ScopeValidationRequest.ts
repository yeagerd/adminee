/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { IntegrationProvider } from './IntegrationProvider';
/**
 * Request model for validating OAuth scopes.
 */
export type ScopeValidationRequest = {
    /**
     * OAuth provider
     */
    provider: IntegrationProvider;
    /**
     * Scopes to validate
     */
    scopes: Array<string>;
};

