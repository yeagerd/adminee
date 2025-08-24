/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ProviderListResponse } from '../models/ProviderListResponse';
import type { ScopeValidationRequest } from '../models/ScopeValidationRequest';
import type { ScopeValidationResponse } from '../models/ScopeValidationResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class IntegrationProvidersService {
    /**
     * List Oauth Providers
     * List all available OAuth providers.
     *
     * Returns configuration information for all supported OAuth providers
     * including availability status, supported scopes, and default settings.
     *
     * **Response:**
     * - Provider display names and identifiers
     * - Availability status (configured and enabled)
     * - Supported OAuth scopes with descriptions
     * - Default scope configurations
     * @returns ProviderListResponse Successful Response
     * @throws ApiError
     */
    public static listOauthProvidersV1IntegrationsProvidersGet(): CancelablePromise<ProviderListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/v1/integrations/providers',
            errors: {
                401: `Authentication required`,
                422: `Validation error`,
            },
        });
    }
    /**
     * Validate Oauth Scopes
     * Validate OAuth scopes for a provider.
     *
     * Checks requested scopes against provider configuration and returns
     * validation results with warnings and recommendations.
     *
     * **Request Body:**
     * - `provider`: OAuth provider to validate against
     * - `scopes`: List of scope names to validate
     *
     * **Response:**
     * - `valid_scopes`: Scopes that are supported by provider
     * - `invalid_scopes`: Scopes that are not supported
     * - `required_scopes`: Required scopes that will be automatically added
     * - `sensitive_scopes`: Scopes that access sensitive data
     * - `warnings`: Validation warnings and recommendations
     * @param requestBody
     * @returns ScopeValidationResponse Successful Response
     * @throws ApiError
     */
    public static validateOauthScopesV1IntegrationsValidateScopesPost(
        requestBody: ScopeValidationRequest,
    ): CancelablePromise<ScopeValidationResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/v1/integrations/validate-scopes',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `Authentication required`,
                422: `Validation error`,
            },
        });
    }
}
