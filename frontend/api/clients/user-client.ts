import { Integration, IntegrationListResponse, OAuthCallbackResponse, OAuthStartResponse, User } from '../types/common';
import { GatewayClient } from './gateway-client';

export class UserClient extends GatewayClient {
    // User Service
    async getCurrentUser() {
        return this.request('/api/v1/users/me');
    }

    async updateUser(userData: Record<string, unknown>) {
        return this.request('/api/v1/users/me', {
            method: 'PUT',
            body: userData,
        });
    }

    async getUserPreferences() {
        return this.request('/api/v1/users/me/preferences');
    }

    async updateUserPreferences(preferences: Record<string, unknown>) {
        return this.request('/api/v1/users/me/preferences', {
            method: 'PUT',
            body: preferences,
        });
    }

    // Integration Management
    async getIntegrations(): Promise<IntegrationListResponse> {
        return this.request<IntegrationListResponse>('/api/v1/users/me/integrations');
    }

    async startOAuthFlow(provider: string, scopes: string[]) {
        // Use a dedicated integration callback URL to avoid conflicts with NextAuth
        const redirectUri = `${window.location.origin}/integrations/callback`;

        return this.request('/api/v1/users/me/integrations/oauth/start', {
            method: 'POST',
            body: {
                provider,
                scopes,
                redirect_uri: redirectUri,
            },
        });
    }

    async completeOAuthFlow(provider: string, code: string, state: string): Promise<OAuthCallbackResponse> {
        return this.request<OAuthCallbackResponse>(`/api/v1/users/me/integrations/oauth/callback?provider=${provider}`, {
            method: 'POST',
            body: { code, state },
        });
    }

    async disconnectIntegration(provider: string) {
        return this.request(`/api/v1/users/me/integrations/${provider}`, {
            method: 'DELETE',
        });
    }

    async refreshIntegrationTokens(provider: string) {
        return this.request(`/api/v1/users/me/integrations/${provider}/refresh`, {
            method: 'PUT',
        });
    }

    async getProviderScopes(provider: string) {
        return this.request<{
            provider: string;
            scopes: Array<{
                name: string;
                description: string;
                required: boolean;
                sensitive: boolean;
            }>;
            default_scopes: string[];
        }>(`/api/v1/users/me/integrations/${provider}/scopes`);
    }
}
