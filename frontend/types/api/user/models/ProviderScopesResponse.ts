/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { IntegrationScopeResponse } from './IntegrationScopeResponse';
/**
 * Response model for provider scopes endpoint.
 */
export type ProviderScopesResponse = {
    /**
     * Provider name
     */
    provider: string;
    /**
     * Available scopes for this provider
     */
    scopes: Array<IntegrationScopeResponse>;
    /**
     * Default scopes for this provider
     */
    default_scopes: Array<string>;
};

