/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request model for OAuth callback handling.
 */
export type OAuthCallbackRequest = {
    /**
     * OAuth authorization code
     */
    code?: (string | null);
    /**
     * OAuth state parameter
     */
    state: string;
    /**
     * OAuth error if any
     */
    error?: (string | null);
    /**
     * OAuth error description
     */
    error_description?: (string | null);
};

