import { getSession } from 'next-auth/react';

const USER_SERVICE_URL = process.env.NEXT_PUBLIC_USER_SERVICE_URL || 'http://localhost:8001';

interface ApiClientOptions {
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
    body?: any;
    headers?: Record<string, string>;
}

class ApiClient {
    private baseUrl: string;

    constructor(baseUrl: string = USER_SERVICE_URL) {
        this.baseUrl = baseUrl;
    }

    private async getAuthHeaders(): Promise<Record<string, string>> {
        const session = await getSession();
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
        };

        // Add API key if available
        if (process.env.NEXT_PUBLIC_USER_SERVICE_API_KEY) {
            headers['X-API-Key'] = process.env.NEXT_PUBLIC_USER_SERVICE_API_KEY;
        }

        // Add user context if available
        if (session?.providerUserId) {
            headers['X-User-ID'] = session.providerUserId;
        }

        return headers;
    }

    private async request<T>(endpoint: string, options: ApiClientOptions = {}): Promise<T> {
        const { method = 'GET', body, headers: customHeaders } = options;

        const authHeaders = await this.getAuthHeaders();
        const headers = { ...authHeaders, ...customHeaders };

        const config: RequestInit = {
            method,
            headers,
        };

        if (body && method !== 'GET') {
            config.body = JSON.stringify(body);
        }

        const url = `${this.baseUrl}${endpoint}`;

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`API Error (${response.status}): ${errorText}`);
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return response.json();
            }

            return response.text() as T;
        } catch (error) {
            console.error('API Client Error:', error);
            throw error;
        }
    }

    // User Management
    async getCurrentUser() {
        const session = await getSession();
        if (!session?.providerUserId) {
            throw new Error('No authenticated user');
        }
        return this.request(`/users/external/${session.providerUserId}`);
    }

    async updateUser(userData: any) {
        const session = await getSession();
        if (!session?.providerUserId) {
            throw new Error('No authenticated user');
        }
        return this.request(`/users/external/${session.providerUserId}`, {
            method: 'PUT',
            body: userData,
        });
    }

    // Integration Management
    async getIntegrations() {
        const session = await getSession();
        if (!session?.providerUserId) {
            throw new Error('No authenticated user');
        }
        return this.request(`/users/${session.providerUserId}/integrations`);
    }

    async startOAuthFlow(provider: string, scopes: string[]) {
        const session = await getSession();
        if (!session?.providerUserId) {
            throw new Error('No authenticated user');
        }
        return this.request(`/users/${session.providerUserId}/integrations/oauth/start`, {
            method: 'POST',
            body: {
                provider,
                scopes,
                redirect_uri: `${window.location.origin}/integrations/callback`,
            },
        });
    }

    async completeOAuthFlow(provider: string, code: string, state: string) {
        const session = await getSession();
        if (!session?.providerUserId) {
            throw new Error('No authenticated user');
        }
        return this.request(`/users/${session.providerUserId}/integrations/oauth/callback?provider=${provider}`, {
            method: 'POST',
            body: { code, state },
        });
    }

    async disconnectIntegration(provider: string) {
        const session = await getSession();
        if (!session?.providerUserId) {
            throw new Error('No authenticated user');
        }
        return this.request(`/users/${session.providerUserId}/integrations/${provider}`, {
            method: 'DELETE',
        });
    }

    async refreshIntegrationTokens(provider: string) {
        const session = await getSession();
        if (!session?.providerUserId) {
            throw new Error('No authenticated user');
        }
        return this.request(`/users/${session.providerUserId}/integrations/${provider}/refresh`, {
            method: 'POST',
        });
    }

    // Health Check
    async healthCheck() {
        return this.request('/health');
    }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export types for TypeScript
export interface Integration {
    id: string;
    provider: string;
    status: string;
    scopes: string[];
    last_sync_at?: string;
    error_message?: string;
}

export interface User {
    id: string;
    email: string;
    first_name?: string;
    last_name?: string;
    profile_image_url?: string;
    onboarding_completed: boolean;
    onboarding_step?: string;
}

export interface OAuthStartResponse {
    authorization_url: string;
    state: string;
    expires_at: string;
    requested_scopes: string[];
}

export default apiClient; 