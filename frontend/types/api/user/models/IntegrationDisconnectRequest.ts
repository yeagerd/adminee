/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request model for disconnecting integration.
 */
export type IntegrationDisconnectRequest = {
    /**
     * Whether to revoke tokens with provider
     */
    revoke_tokens?: boolean;
    /**
     * Whether to delete associated user data
     */
    delete_data?: boolean;
};

