/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { IntegrationResponse } from './IntegrationResponse';
/**
 * Response model for listing user integrations.
 */
export type IntegrationListResponse = {
    /**
     * List of user integrations
     */
    integrations?: Array<IntegrationResponse>;
    /**
     * Total number of integrations
     */
    total: number;
    /**
     * Number of active integrations
     */
    active_count: number;
    /**
     * Number of integrations with errors
     */
    error_count: number;
};

