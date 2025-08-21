import {
    IntegrationListResponse,
    IntegrationProvider,
    IntegrationScopeResponse,
    OAuthCallbackRequest,
    OAuthCallbackResponse,
    OAuthStartRequest,
    OAuthStartResponse,
    UserPreferencesResponse,
    UserPreferencesUpdate,
    UserResponse
} from '../../types/api/user';
import { GatewayClient } from './gateway-client';

export class UserClient extends GatewayClient {
    // User Service
    async getCurrentUser(): Promise<UserResponse> {
        return this.request<UserResponse>('/api/v1/users/me');
    }

    async updateUser(userData: Partial<UserResponse>) {
        return this.request<UserResponse>('/api/v1/users/me', {
            method: 'PUT',
            body: userData,
        });
    }

    async getUserPreferences(): Promise<UserPreferencesResponse> {
        return this.request<UserPreferencesResponse>('/api/v1/users/me/preferences');
    }

    async updateUserPreferences(preferences: UserPreferencesUpdate): Promise<UserPreferencesResponse> {
        return this.request<UserPreferencesResponse>('/api/v1/users/me/preferences', {
            method: 'PUT',
            body: preferences,
        });
    }

    // Integration Management
    async getIntegrations(): Promise<IntegrationListResponse> {
        return this.request<IntegrationListResponse>('/api/v1/users/me/integrations');
    }

    async startOAuthFlow(provider: IntegrationProvider, scopes: string[]): Promise<OAuthStartResponse> {
        // Use a dedicated integration callback URL to avoid conflicts with NextAuth
        const redirectUri = `${window.location.origin}/integrations/callback`;

        const request: OAuthStartRequest = {
            provider,
            scopes,
            redirect_uri: redirectUri,
        };

        return this.request<OAuthStartResponse>('/api/v1/users/me/integrations/oauth/start', {
            method: 'POST',
            body: request,
        });
    }

    async completeOAuthFlow(provider: IntegrationProvider, code: string, state: string): Promise<OAuthCallbackResponse> {
        const request: OAuthCallbackRequest = { code, state };
        return this.request<OAuthCallbackResponse>(`/api/v1/users/me/integrations/oauth/callback?provider=${provider}`, {
            method: 'POST',
            body: request,
        });
    }

    async disconnectIntegration(provider: IntegrationProvider) {
        return this.request(`/api/v1/users/me/integrations/${provider}`, {
            method: 'DELETE',
        });
    }

    async refreshIntegrationTokens(provider: IntegrationProvider) {
        return this.request(`/api/v1/users/me/integrations/${provider}/refresh`, {
            method: 'PUT',
        });
    }

    async getProviderScopes(provider: IntegrationProvider): Promise<IntegrationScopeResponse> {
        return this.request<IntegrationScopeResponse>(`/api/v1/users/me/integrations/${provider}/scopes`);
    }
}
