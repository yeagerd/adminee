/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { IntegrationDisconnectRequest } from '../models/IntegrationDisconnectRequest';
import type { IntegrationDisconnectResponse } from '../models/IntegrationDisconnectResponse';
import type { IntegrationHealthResponse } from '../models/IntegrationHealthResponse';
import type { IntegrationListResponse } from '../models/IntegrationListResponse';
import type { IntegrationProvider } from '../models/IntegrationProvider';
import type { IntegrationResponse } from '../models/IntegrationResponse';
import type { IntegrationStatus } from '../models/IntegrationStatus';
import type { OAuthCallbackRequest } from '../models/OAuthCallbackRequest';
import type { OAuthCallbackResponse } from '../models/OAuthCallbackResponse';
import type { OAuthStartRequest } from '../models/OAuthStartRequest';
import type { OAuthStartResponse } from '../models/OAuthStartResponse';
import type { TokenRefreshRequest } from '../models/TokenRefreshRequest';
import type { TokenRefreshResponse } from '../models/TokenRefreshResponse';
import type { UserCreate } from '../models/UserCreate';
import type { UserListResponse } from '../models/UserListResponse';
import type { UserResponse } from '../models/UserResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class UsersService {
    /**
     * Get current user profile
     * Get the profile of the currently authenticated user.
     * @returns UserResponse Current user profile retrieved successfully
     * @throws ApiError
     */
    public static getCurrentUserProfileV1UsersMeGet(): CancelablePromise<UserResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/users/me',
            errors: {
                401: `Authentication required`,
                404: `User not found`,
            },
        });
    }
    /**
     * Get current user integrations
     * Get all integrations for the currently authenticated user.
     * @param provider Filter by provider
     * @param status Filter by status
     * @param includeTokenInfo Include token metadata
     * @returns IntegrationListResponse Current user integrations retrieved successfully
     * @throws ApiError
     */
    public static getCurrentUserIntegrationsV1UsersMeIntegrationsGet(
        provider?: (IntegrationProvider | null),
        status?: (IntegrationStatus | null),
        includeTokenInfo: boolean = true,
    ): CancelablePromise<IntegrationListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/users/me/integrations',
            query: {
                'provider': provider,
                'status': status,
                'include_token_info': includeTokenInfo,
            },
            errors: {
                401: `Authentication required`,
                404: `User not found`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Disconnect current user integration
     * Disconnect an OAuth integration for the currently authenticated user.
     * @param provider OAuth provider
     * @param requestBody
     * @returns IntegrationDisconnectResponse Integration disconnected successfully
     * @throws ApiError
     */
    public static disconnectCurrentUserIntegrationV1UsersMeIntegrationsProviderDelete(
        provider: IntegrationProvider,
        requestBody?: (IntegrationDisconnectRequest | null),
    ): CancelablePromise<IntegrationDisconnectResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/v1/users/me/integrations/{provider}',
            path: {
                'provider': provider,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Authentication required`,
                404: `Integration not found`,
                422: `Validation error`,
            },
        });
    }
    /**
     * Get current user specific integration
     * Get details for a specific integration of the currently authenticated user.
     * @param provider OAuth provider
     * @returns IntegrationResponse Integration details retrieved successfully
     * @throws ApiError
     */
    public static getCurrentUserSpecificIntegrationV1UsersMeIntegrationsProviderGet(
        provider: IntegrationProvider,
    ): CancelablePromise<IntegrationResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/users/me/integrations/{provider}',
            path: {
                'provider': provider,
            },
            errors: {
                401: `Authentication required`,
                404: `Integration not found`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Refresh current user integration tokens
     * Refresh access tokens for an integration of the currently authenticated user.
     * @param provider OAuth provider
     * @param requestBody
     * @returns TokenRefreshResponse Tokens refreshed successfully
     * @throws ApiError
     */
    public static refreshCurrentUserIntegrationTokensV1UsersMeIntegrationsProviderRefreshPut(
        provider: IntegrationProvider,
        requestBody?: (TokenRefreshRequest | null),
    ): CancelablePromise<TokenRefreshResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/v1/users/me/integrations/{provider}/refresh',
            path: {
                'provider': provider,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Authentication required`,
                404: `Integration not found`,
                422: `Validation error`,
            },
        });
    }
    /**
     * Check current user integration health
     * Check the health status of an integration for the currently authenticated user.
     * @param provider OAuth provider
     * @returns IntegrationHealthResponse Health check completed successfully
     * @throws ApiError
     */
    public static checkCurrentUserIntegrationHealthV1UsersMeIntegrationsProviderHealthGet(
        provider: IntegrationProvider,
    ): CancelablePromise<IntegrationHealthResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/users/me/integrations/{provider}/health',
            path: {
                'provider': provider,
            },
            errors: {
                401: `Authentication required`,
                404: `Integration not found`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get available OAuth scopes for provider
     * Get the list of available OAuth scopes for a specific provider.
     * @param provider OAuth provider
     * @returns any Scopes retrieved successfully
     * @throws ApiError
     */
    public static getProviderScopesV1UsersMeIntegrationsProviderScopesGet(
        provider: IntegrationProvider,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/users/me/integrations/{provider}/scopes',
            path: {
                'provider': provider,
            },
            errors: {
                401: `Authentication required`,
                404: `Provider not found`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Search users
     * Search users with cursor-based pagination. For admin/service use.
     * @param cursor Cursor token for pagination
     * @param limit Number of users per page
     * @param direction Pagination direction
     * @param query Search query
     * @param email Filter by email
     * @param onboardingCompleted Filter by onboarding status
     * @returns UserListResponse User search results retrieved successfully
     * @throws ApiError
     */
    public static searchUsersV1UsersSearchGet(
        cursor?: (string | null),
        limit?: (number | null),
        direction?: (string | null),
        query?: (string | null),
        email?: (string | null),
        onboardingCompleted?: (boolean | null),
    ): CancelablePromise<UserListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/users/search',
            query: {
                'cursor': cursor,
                'limit': limit,
                'direction': direction,
                'query': query,
                'email': email,
                'onboarding_completed': onboardingCompleted,
            },
            errors: {
                400: `Invalid cursor token`,
                401: `Authentication required`,
                422: `Validation error in search parameters`,
            },
        });
    }
    /**
     * Create or upsert user (OAuth/NextAuth)
     * Create a new user or return existing user by external_auth_id and auth_provider. Protected endpoint for OAuth/NextAuth flows with service authentication.
     * @param requestBody
     * @returns any User already exists, returned successfully
     * @returns UserResponse User created successfully
     * @throws ApiError
     */
    public static createOrUpsertUserV1UsersPost(
        requestBody: UserCreate,
    ): CancelablePromise<any | UserResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/users/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Service authentication required`,
                409: `Email collision detected`,
                422: `Validation error in request data`,
            },
        });
    }
    /**
     * Start OAuth flow for current user
     * Start OAuth authorization flow for the currently authenticated user.
     * @param requestBody
     * @returns OAuthStartResponse OAuth flow started successfully
     * @throws ApiError
     */
    public static startCurrentUserOauthFlowV1UsersMeIntegrationsOauthStartPost(
        requestBody: OAuthStartRequest,
    ): CancelablePromise<OAuthStartResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/users/me/integrations/oauth/start',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Authentication required`,
                422: `Validation error`,
            },
        });
    }
    /**
     * Complete OAuth flow for current user
     * Complete OAuth authorization flow for the currently authenticated user.
     * @param provider OAuth provider
     * @param requestBody
     * @returns OAuthCallbackResponse OAuth flow completed successfully
     * @throws ApiError
     */
    public static completeCurrentUserOauthFlowV1UsersMeIntegrationsOauthCallbackPost(
        provider: IntegrationProvider,
        requestBody: OAuthCallbackRequest,
    ): CancelablePromise<OAuthCallbackResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/users/me/integrations/oauth/callback',
            query: {
                'provider': provider,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Authentication required`,
                422: `Validation error`,
            },
        });
    }
}
