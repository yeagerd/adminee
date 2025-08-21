/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for OAuth scope information.
 */
export type IntegrationScopeResponse = {
    /**
     * Scope name
     */
    name: string;
    /**
     * Human-readable scope description
     */
    description: string;
    /**
     * Whether scope is required
     */
    required: boolean;
    /**
     * Whether scope accesses sensitive data
     */
    sensitive: boolean;
    /**
     * Whether user has granted this scope
     */
    granted: boolean;
};

