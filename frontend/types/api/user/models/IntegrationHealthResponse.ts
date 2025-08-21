/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { IntegrationProvider } from './IntegrationProvider';
import type { IntegrationStatus } from './IntegrationStatus';
/**
 * Response model for integration health check.
 */
export type IntegrationHealthResponse = {
    /**
     * Integration ID
     */
    integration_id: number;
    /**
     * OAuth provider
     */
    provider: IntegrationProvider;
    /**
     * Integration status
     */
    status: IntegrationStatus;
    /**
     * Whether integration is healthy
     */
    healthy: boolean;
    /**
     * Last health check time
     */
    last_check_at: string;
    /**
     * List of health issues
     */
    issues?: Array<string>;
    /**
     * Recommended actions
     */
    recommendations?: Array<string>;
};

