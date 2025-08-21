/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { IntegrationProviderInfo } from './IntegrationProviderInfo';
/**
 * Response model for listing available OAuth providers.
 */
export type ProviderListResponse = {
    /**
     * Available OAuth providers
     */
    providers?: Array<IntegrationProviderInfo>;
    /**
     * Total number of providers
     */
    total: number;
    /**
     * Number of available providers
     */
    available_count: number;
};

