/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { InternalTokenRefreshRequest } from '../models/InternalTokenRefreshRequest';
import type { InternalTokenRequest } from '../models/InternalTokenRequest';
import type { InternalTokenResponse } from '../models/InternalTokenResponse';
import type { InternalUserStatusResponse } from '../models/InternalUserStatusResponse';
import type { PreferencesResetRequest } from '../models/PreferencesResetRequest';
import type { UserCreate } from '../models/UserCreate';
import type { UserCreateResponse } from '../models/UserCreateResponse';
import type { UserPreferencesResponse } from '../models/UserPreferencesResponse';
import type { UserPreferencesUpdate } from '../models/UserPreferencesUpdate';
import type { UserResponse } from '../models/UserResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class InternalService {
    /**
     * Get User Token
     * Get a valid access token for a user and provider.
     *
     * This endpoint is used by other services to retrieve tokens for API operations.
     * @param requestBody
     * @returns InternalTokenResponse Successful Response
     * @throws ApiError
     */
    public static getUserTokenV1InternalTokensGetPost(
        requestBody: InternalTokenRequest,
    ): CancelablePromise<InternalTokenResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/internal/tokens/get',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Service authentication required`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Refresh User Tokens
     * Refresh user tokens for other services.
     *
     * Manually refresh OAuth access tokens using stored refresh tokens.
     * Useful for recovering from token expiration or API errors.
     *
     * **Authentication:**
     * - Requires service-to-service API key authentication
     * - Only authorized services can refresh user tokens
     *
     * **Request Body:**
     * - `user_id`: User identifier
     * - `provider`: OAuth provider (google, microsoft, etc.)
     * - `force`: Force refresh even if not near expiration (default: false)
     *
     * **Response:**
     * - `success`: Whether token refresh succeeded
     * - `access_token`: New OAuth access token (if successful)
     * - `refresh_token`: Refresh token (if available)
     * - `expires_at`: New token expiration time
     * - `error`: Error message (if failed)
     *
     * **Features:**
     * - Uses stored refresh tokens for token exchange
     * - Updates token records with new expiration times
     * - Comprehensive error handling and logging
     * - Returns updated token information
     * @param requestBody
     * @returns InternalTokenResponse Successful Response
     * @throws ApiError
     */
    public static refreshUserTokensV1InternalTokensRefreshPost(
        requestBody: InternalTokenRefreshRequest,
    ): CancelablePromise<InternalTokenResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/internal/tokens/refresh',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Service authentication required`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get User Status
     * Get user integration status for other services.
     *
     * Provides comprehensive integration status information including
     * active integrations, error states, and provider availability.
     *
     * **Authentication:**
     * - Requires service-to-service API key authentication
     * - Only authorized services can retrieve user status
     *
     * **Path Parameters:**
     * - `user_id`: User identifier
     *
     * **Response:**
     * - `user_id`: User identifier
     * - `active_integrations`: Number of active integrations
     * - `total_integrations`: Total number of integrations
     * - `providers`: List of available providers
     * - `has_errors`: Whether any integrations have errors
     * - `last_sync_at`: Last successful sync time
     *
     * **Use Cases:**
     * - Check user integration health before making API calls
     * - Determine available OAuth providers for a user
     * - Monitor integration error states
     * - Track sync activity across services
     * @param userId
     * @returns InternalUserStatusResponse Successful Response
     * @throws ApiError
     */
    public static getUserStatusV1InternalUsersUserIdStatusGet(
        userId: string,
    ): CancelablePromise<InternalUserStatusResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/internal/users/{user_id}/status',
            path: {
                'user_id': userId,
            },
            errors: {
                401: `Service authentication required`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get User By External Auth Id
     * Get user information by external_auth_id (internal service endpoint).
     *
     * This endpoint always returns 200 with user information or null,
     * avoiding 404 logs for missing users.
     *
     * Returns:
     * User data if found, or {"exists": false} if not found
     * @param externalAuthId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getUserByExternalAuthIdV1InternalUsersByExternalIdExternalAuthIdGet(
        externalAuthId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/internal/users/by-external-id/{external_auth_id}',
            path: {
                'external_auth_id': externalAuthId,
            },
            errors: {
                401: `Service authentication required`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Check User Exists
     * Check if a user exists by email (primary endpoint for user existence checks).
     *
     * This endpoint always returns 200 with a detailed response,
     * avoiding 404 logs for missing users. Use this instead of GET /users/id
     * when you only need to check existence.
     *
     * Returns:
     * {"exists": true/false, "user_id": "id_if_exists", "provider": "provider_if_exists"}
     * @param email Email address to check
     * @param provider OAuth provider (google, microsoft, etc.)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static checkUserExistsV1InternalUsersExistsGet(
        email: string,
        provider?: (string | null),
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/internal/users/exists',
            query: {
                'email': email,
                'provider': provider,
            },
            errors: {
                401: `Service authentication required`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get User By Email Internal
     * Get user by exact email lookup (internal service endpoint).
     *
     * ⚠️  DEPRECATED: Use GET /v1/internal/users/exists instead to avoid 404 error logs.
     * This endpoint will be removed in a future version.
     *
     * This endpoint provides a clean RESTful way to find users by email address
     * without exposing internal email normalization implementation details.
     * Perfect for NextAuth integration where you need to check user existence
     * before deciding whether to create a new user.
     *
     * **Authentication:**
     * - Requires service-to-service API key authentication
     * - Only authorized services (frontend, chat, office) can lookup users
     * - Never accepts user JWTs
     *
     * Args:
     * email: Email address to lookup
     * provider: OAuth provider for context (optional)
     *
     * Returns:
     * UserResponse if user found
     *
     * Raises:
     * 404: If no user found for the email
     * 422: If email format is invalid
     * @param email Email address to lookup
     * @param provider OAuth provider (google, microsoft, etc.)
     * @returns UserResponse Successful Response
     * @throws ApiError
     */
    public static getUserByEmailInternalV1InternalUsersIdGet(
        email: string,
        provider?: (string | null),
    ): CancelablePromise<UserResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/internal/users/id',
            query: {
                'email': email,
                'provider': provider,
            },
            errors: {
                401: `Service authentication required`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Or Upsert User Internal
     * Create a new user or return existing user by external_auth_id and auth_provider (internal service endpoint).
     *
     * This is a protected endpoint designed for OAuth/NextAuth flows where
     * we want to create users if they don't exist, or return existing
     * users if they do. Requires service authentication (API key).
     *
     * **Authentication:**
     * - Requires service-to-service API key authentication
     * - Only authorized services (frontend, chat, office) can create users
     * - Never accepts user JWTs
     *
     * **Response Status Codes:**
     * - 200 (OK): Existing user found and returned
     * - 201 (Created): New user created successfully
     * - 409 (Conflict): Email collision detected
     * - 422 (Validation Error): Invalid request data
     * - 500 (Internal Server Error): Unexpected error
     * @param requestBody
     * @returns UserCreateResponse Successful Response
     * @throws ApiError
     */
    public static createOrUpsertUserInternalV1InternalUsersPost(
        requestBody: UserCreate,
    ): CancelablePromise<UserCreateResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/internal/users/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Service authentication required`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update User Preferences Internal
     * Internal service endpoint to update user preferences by user_id.
     * Requires service-to-service API key authentication.
     * @param userId
     * @param requestBody
     * @returns UserPreferencesResponse Successful Response
     * @throws ApiError
     */
    public static updateUserPreferencesInternalV1InternalUsersUserIdPreferencesPut(
        userId: string,
        requestBody: UserPreferencesUpdate,
    ): CancelablePromise<UserPreferencesResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/v1/internal/users/{user_id}/preferences',
            path: {
                'user_id': userId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Service authentication required`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get User Preferences Internal
     * Get user preferences for other services.
     *
     * Internal service endpoint to retrieve user preferences with service authentication.
     * Used by chat service and other internal services to get user timezone and settings.
     *
     * **Authentication:**
     * - Requires service-to-service API key authentication
     * - Only authorized services can retrieve user preferences
     *
     * **Path Parameters:**
     * - `user_id`: User identifier (external auth ID)
     *
     * **Response:**
     * - User preferences object or null if not found
     * - Returns 404 if user not found (normal for new users)
     *
     * **Use Cases:**
     * - Chat service getting user timezone for scheduling
     * - Office service getting user notification preferences
     * - Any service needing user settings for personalization
     * @param userId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getUserPreferencesInternalV1InternalUsersUserIdPreferencesGet(
        userId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/internal/users/{user_id}/preferences',
            path: {
                'user_id': userId,
            },
            errors: {
                401: `Service authentication required`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Reset User Preferences Internal
     * Internal service endpoint to reset user preferences by user_id.
     * Requires service-to-service API key authentication.
     * @param userId
     * @param requestBody
     * @returns UserPreferencesResponse Successful Response
     * @throws ApiError
     */
    public static resetUserPreferencesInternalV1InternalUsersUserIdPreferencesResetPost(
        userId: string,
        requestBody: PreferencesResetRequest,
    ): CancelablePromise<UserPreferencesResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/internal/users/{user_id}/preferences/reset',
            path: {
                'user_id': userId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Service authentication required`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get User Integrations Internal
     * Get user integrations for other services.
     *
     * Internal service endpoint to retrieve user integrations with service authentication.
     * Used by chat service and other internal services to determine available providers.
     *
     * **Authentication:**
     * - Requires service-to-service API key authentication
     * - Only authorized services can retrieve user integrations
     *
     * **Path Parameters:**
     * - `user_id`: User identifier (external auth ID)
     *
     * **Response:**
     * - List of user integrations with status and provider information
     * - Returns empty list if user not found or no integrations
     *
     * **Use Cases:**
     * - Chat service determining available calendar providers
     * - Office service checking user's connected accounts
     * - Any service needing to know user's OAuth connections
     * @param userId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getUserIntegrationsInternalV1InternalUsersUserIdIntegrationsGet(
        userId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/internal/users/{user_id}/integrations',
            path: {
                'user_id': userId,
            },
            errors: {
                401: `Service authentication required`,
                422: `Validation Error`,
            },
        });
    }
}
