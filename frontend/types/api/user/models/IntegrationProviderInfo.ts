/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { IntegrationProvider } from './IntegrationProvider';
import type { IntegrationScopeResponse } from './IntegrationScopeResponse';
/**
 * Information about an OAuth provider.
 */
export type IntegrationProviderInfo = {
    /**
     * Provider display name
     */
    name: string;
    /**
     * Provider identifier
     */
    provider: IntegrationProvider;
    /**
     * Whether provider is configured and available
     */
    available: boolean;
    /**
     * Available scopes for this provider
     */
    supported_scopes?: Array<IntegrationScopeResponse>;
    /**
     * Default scopes requested
     */
    default_scopes?: Array<string>;
};

