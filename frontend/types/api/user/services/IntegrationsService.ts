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
import type { IntegrationStatsResponse } from '../models/IntegrationStatsResponse';
import type { IntegrationStatus } from '../models/IntegrationStatus';
import type { OAuthCallbackRequest } from '../models/OAuthCallbackRequest';
import type { OAuthCallbackResponse } from '../models/OAuthCallbackResponse';
import type { OAuthStartRequest } from '../models/OAuthStartRequest';
import type { OAuthStartResponse } from '../models/OAuthStartResponse';
import type { TokenRefreshRequest } from '../models/TokenRefreshRequest';
import type { TokenRefreshResponse } from '../models/TokenRefreshResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class IntegrationsService {
    /**
     * List User Integrations
     * List all integrations for a user.
     *
     * Returns comprehensive integration information including status, metadata,
     * token availability, and error details with optional filtering.
     *
     * **Query Parameters:**
     * - `provider`: Filter integrations by specific OAuth provider
     * - `status`: Filter integrations by status (active, inactive, error, pending)
     * - `include_token_info`: Include token expiration and availability info
     *
     * **Response includes:**
     * - Integration details and provider information
     * - OAuth scope information and external user data
     * - Token metadata (expiration, availability) without actual tokens
     * - Error information and health status
     * - Last sync timestamps and activity
     * @param userId
     * @param provider Filter by provider
     * @param status Filter by status
     * @param includeTokenInfo Include token metadata
     * @returns IntegrationListResponse Successful Response
     * @throws ApiError
     */
    public static listUserIntegrationsV1UsersUserIdIntegrationsGet(
        userId: string,
        provider?: (IntegrationProvider | null),
        status?: (IntegrationStatus | null),
        includeTokenInfo: boolean = true,
    ): CancelablePromise<IntegrationListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/users/{user_id}/integrations/',
            path: {
                'user_id': userId,
            },
            query: {
                'provider': provider,
                'status': status,
                'include_token_info': includeTokenInfo,
            },
            errors: {
                401: `Authentication required`,
                403: `Access forbidden - insufficient permissions`,
                404: `User or integration not found`,
                422: `Validation error`,
            },
        });
    }
    /**
     * Start Oauth Flow
     * Start OAuth authorization flow for a provider.
     *
     * Initiates the OAuth 2.0 authorization code flow with PKCE security.
     * Returns authorization URL that the client should redirect the user to.
     *
     * **Security Features:**
     * - PKCE challenge/verifier generation
     * - Secure state parameter with expiration
     * - Scope validation and provider verification
     * - User-specific encryption keys
     *
     * **Request Body:**
     * - `provider`: OAuth provider (google, microsoft, etc.)
     * - `redirect_uri`: OAuth callback URL (must be whitelisted)
     * - `scopes`: Requested OAuth scopes (optional, uses defaults)
     * - `state_data`: Additional data to preserve through flow
     *
     * **Response:**
     * - `authorization_url`: URL to redirect user for authorization
     * - `state`: OAuth state parameter (preserve for callback)
     * - `expires_at`: State expiration time
     * - `requested_scopes`: Final scope list that will be requested
     * @param userId
     * @param requestBody
     * @returns OAuthStartResponse Successful Response
     * @throws ApiError
     */
    public static startOauthFlowV1UsersUserIdIntegrationsOauthStartPost(
        userId: string,
        requestBody: OAuthStartRequest,
    ): CancelablePromise<OAuthStartResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/users/{user_id}/integrations/oauth/start',
            path: {
                'user_id': userId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Authentication required`,
                403: `Access forbidden - insufficient permissions`,
                404: `User or integration not found`,
                422: `Validation error`,
            },
        });
    }
    /**
     * Complete Oauth Flow
     * Complete OAuth authorization flow and create integration.
     *
     * Handles the OAuth callback with authorization code exchange, token storage,
     * and integration setup. Creates or updates the user's integration record.
     *
     * **Security Features:**
     * - State validation and anti-CSRF protection
     * - Secure token storage with user-specific encryption
     * - Comprehensive error handling and logging
     * - Integration status tracking
     *
     * **Request Body:**
     * - `code`: Authorization code from OAuth provider
     * - `state`: OAuth state parameter from start flow
     * - `error`: OAuth error code (if authorization failed)
     * - `error_description`: Human-readable error description
     *
     * **Response:**
     * - `success`: Whether OAuth flow completed successfully
     * - `integration_id`: Created/updated integration ID
     * - `status`: Integration status after completion
     * - `scopes`: Actually granted OAuth scopes
     * - `external_user_info`: User information from provider
     * - `error`: Error message if flow failed
     * @param userId
     * @param provider OAuth provider
     * @param requestBody
     * @returns OAuthCallbackResponse Successful Response
     * @throws ApiError
     */
    public static completeOauthFlowV1UsersUserIdIntegrationsOauthCallbackPost(
        userId: string,
        provider: IntegrationProvider,
        requestBody: OAuthCallbackRequest,
    ): CancelablePromise<OAuthCallbackResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/users/{user_id}/integrations/oauth/callback',
            path: {
                'user_id': userId,
            },
            query: {
                'provider': provider,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Authentication required`,
                403: `Access forbidden - insufficient permissions`,
                404: `User or integration not found`,
                422: `Validation error`,
            },
        });
    }
    /**
     * Get Integration Statistics
     * Get comprehensive integration statistics for user.
     *
     * Provides analytics and metrics about all user integrations including
     * status distribution, provider usage, error tracking, and sync activity.
     *
     * **Statistics Include:**
     * - Total integration counts by status and provider
     * - Recent error history and patterns
     * - Synchronization activity and timestamps
     * - Health metrics and trends
     *
     * **Response:**
     * - Counts by status (active, error, pending, etc.)
     * - Counts by provider (Google, Microsoft, etc.)
     * - Recent errors with timestamps and details
     * - Sync statistics and activity metrics
     * @param userId
     * @returns IntegrationStatsResponse Successful Response
     * @throws ApiError
     */
    public static getIntegrationStatisticsV1UsersUserIdIntegrationsStatsGet(
        userId: string,
    ): CancelablePromise<IntegrationStatsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/users/{user_id}/integrations/stats',
            path: {
                'user_id': userId,
            },
            errors: {
                401: `Authentication required`,
                403: `Access forbidden - insufficient permissions`,
                404: `User or integration not found`,
                422: `Validation error`,
            },
        });
    }
    /**
     * Get Specific Integration
     * Get details for a specific integration.
     *
     * Returns detailed information about a specific provider integration
     * including status, token info, scopes, and metadata.
     *
     * **Response includes:**
     * - Integration status and provider information
     * - Token availability and expiration details
     * - OAuth scopes and external user information
     * - Error details and health status
     * - Last sync timestamps and activity
     * @param userId
     * @param provider
     * @returns IntegrationResponse Successful Response
     * @throws ApiError
     */
    public static getSpecificIntegrationV1UsersUserIdIntegrationsProviderGet(
        userId: string,
        provider: IntegrationProvider,
    ): CancelablePromise<IntegrationResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/users/{user_id}/integrations/{provider}',
            path: {
                'user_id': userId,
                'provider': provider,
            },
            errors: {
                401: `Authentication required`,
                403: `Access forbidden - insufficient permissions`,
                404: `User or integration not found`,
                422: `Validation error`,
            },
        });
    }
    /**
     * Disconnect Integration
     * Disconnect an OAuth integration.
     *
     * Removes the integration connection and optionally revokes tokens with
     * the provider and deletes associated data.
     *
     * **Request Body (optional):**
     * - `revoke_tokens`: Whether to revoke tokens with provider (default: true)
     * - `delete_data`: Whether to permanently delete integration data (default: false)
     *
     * **Response:**
     * - `success`: Whether disconnection completed successfully
     * - `tokens_revoked`: Whether tokens were successfully revoked
     * - `data_deleted`: Whether integration data was deleted
     * - `disconnected_at`: Timestamp of disconnection
     * - `error`: Error message if disconnection failed
     * @param userId
     * @param provider
     * @param requestBody
     * @returns IntegrationDisconnectResponse Successful Response
     * @throws ApiError
     */
    public static disconnectIntegrationV1UsersUserIdIntegrationsProviderDelete(
        userId: string,
        provider: IntegrationProvider,
        requestBody?: (IntegrationDisconnectRequest | null),
    ): CancelablePromise<IntegrationDisconnectResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/v1/users/{user_id}/integrations/{provider}',
            path: {
                'user_id': userId,
                'provider': provider,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Authentication required`,
                403: `Access forbidden - insufficient permissions`,
                404: `User or integration not found`,
                422: `Validation error`,
            },
        });
    }
    /**
     * Refresh Integration Tokens
     * Refresh access tokens for an integration.
     *
     * Manually refresh OAuth access tokens using stored refresh tokens.
     * Typically used when tokens are near expiration or after API errors.
     *
     * **Request Body (optional):**
     * - `force`: Force refresh even if token not near expiration (default: false)
     *
     * **Response:**
     * - `success`: Whether token refresh completed successfully
     * - `token_expires_at`: New token expiration time
     * - `refreshed_at`: Timestamp of refresh operation
     * - `error`: Error message if refresh failed
     * @param userId
     * @param provider
     * @param requestBody
     * @returns TokenRefreshResponse Successful Response
     * @throws ApiError
     */
    public static refreshIntegrationTokensV1UsersUserIdIntegrationsProviderRefreshPut(
        userId: string,
        provider: IntegrationProvider,
        requestBody?: (TokenRefreshRequest | null),
    ): CancelablePromise<TokenRefreshResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/v1/users/{user_id}/integrations/{provider}/refresh',
            path: {
                'user_id': userId,
                'provider': provider,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Authentication required`,
                403: `Access forbidden - insufficient permissions`,
                404: `User or integration not found`,
                422: `Validation error`,
            },
        });
    }
    /**
     * Check Integration Health
     * Check the health status of an integration.
     *
     * Performs comprehensive health checks including token validity,
     * connection status, and recent activity analysis.
     *
     * **Health Checks:**
     * - Integration status and error state
     * - Token validity and expiration
     * - Recent synchronization activity
     * - Provider connectivity
     *
     * **Response:**
     * - `healthy`: Overall health status boolean
     * - `issues`: List of identified problems
     * - `recommendations`: Suggested actions to resolve issues
     * - `last_check_at`: Timestamp of health check
     * @param userId
     * @param provider
     * @returns IntegrationHealthResponse Successful Response
     * @throws ApiError
     */
    public static checkIntegrationHealthV1UsersUserIdIntegrationsProviderHealthGet(
        userId: string,
        provider: IntegrationProvider,
    ): CancelablePromise<IntegrationHealthResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/users/{user_id}/integrations/{provider}/health',
            path: {
                'user_id': userId,
                'provider': provider,
            },
            errors: {
                401: `Authentication required`,
                403: `Access forbidden - insufficient permissions`,
                404: `User or integration not found`,
                422: `Validation error`,
            },
        });
    }
}
