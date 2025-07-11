import { getSession } from 'next-auth/react';

interface GatewayClientOptions {
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
    body?: unknown;
    headers?: Record<string, string>;
}

class GatewayClient {
    private gatewayUrl: string;

    constructor() {
        // Use gateway URL from environment, fallback to localhost
        this.gatewayUrl = process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:3001';
    }

    private async getAuthHeaders(): Promise<Record<string, string>> {
        const session = await getSession();

        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
        };

        // Add JWT token if available
        if (session?.accessToken) {
            headers['Authorization'] = `Bearer ${session.accessToken}`;
        }

        return headers;
    }

    private async request<T>(endpoint: string, options: GatewayClientOptions = {}): Promise<T> {
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

        const url = `${this.gatewayUrl}${endpoint}`;

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Gateway Error (${response.status}): ${errorText}`);
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return response.json();
            }

            return response.text() as T;
        } catch (error) {
            console.error('Gateway Client Error:', error);
            throw error;
        }
    }

    // Chat Service
    async chat(message: string, threadId?: string, userTimezone?: string) {
        return this.request('/api/chat', {
            method: 'POST',
            body: {
                message,
                thread_id: threadId,
                user_timezone: userTimezone,
            },
        });
    }

    async chatStream(message: string, threadId?: string, userTimezone?: string): Promise<ReadableStream> {
        const session = await getSession();
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
        };

        if (session?.accessToken) {
            headers['Authorization'] = `Bearer ${session.accessToken}`;
        }

        const response = await fetch(`${this.gatewayUrl}/api/chat/stream`, {
            method: 'POST',
            headers,
            body: JSON.stringify({
                message,
                thread_id: threadId,
                user_timezone: userTimezone,
            }),
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Gateway Stream Error (${response.status}): ${errorText}`);
        }

        return response.body!;
    }

    // User Service
    async getCurrentUser() {
        return this.request('/api/users/me');
    }

    async updateUser(userData: Record<string, unknown>) {
        return this.request('/api/users/me', {
            method: 'PUT',
            body: userData,
        });
    }

    async getUserPreferences() {
        return this.request('/api/users/me/preferences');
    }

    async updateUserPreferences(preferences: Record<string, unknown>) {
        return this.request('/api/users/me/preferences', {
            method: 'PUT',
            body: preferences,
        });
    }

    // Integration Management
    async getIntegrations(): Promise<IntegrationListResponse> {
        return this.request<IntegrationListResponse>('/api/users/me/integrations');
    }

    async startOAuthFlow(provider: string, scopes: string[]) {
        return this.request('/api/users/me/integrations/oauth/start', {
            method: 'POST',
            body: {
                provider,
                scopes,
                redirect_uri: `${window.location.origin}/integrations/callback`,
            },
        });
    }

    async completeOAuthFlow(provider: string, code: string, state: string) {
        return this.request(`/api/users/me/integrations/oauth/callback?provider=${provider}`, {
            method: 'POST',
            body: { code, state },
        });
    }

    async disconnectIntegration(provider: string) {
        return this.request(`/api/users/me/integrations/${provider}`, {
            method: 'DELETE',
        });
    }

    async refreshIntegrationTokens(provider: string) {
        return this.request(`/api/users/me/integrations/${provider}/refresh`, {
            method: 'POST',
        });
    }

    // Office Service
    async getCalendarEvents(provider: string, startDate?: string, endDate?: string) {
        const params = new URLSearchParams();
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);

        return this.request(`/api/calendar/events?provider=${provider}&${params.toString()}`);
    }

    async createCalendarEvent(provider: string, eventData: Record<string, unknown>) {
        return this.request('/api/calendar/events', {
            method: 'POST',
            body: {
                provider,
                ...eventData,
            },
        });
    }

    async getEmails(provider: string, limit?: number, offset?: number) {
        const params = new URLSearchParams();
        if (limit) params.append('limit', limit.toString());
        if (offset) params.append('offset', offset.toString());

        return this.request(`/api/email/messages?provider=${provider}&${params.toString()}`);
    }

    async getFiles(provider: string, path?: string) {
        const params = new URLSearchParams();
        if (path) params.append('path', path);

        return this.request(`/api/files?provider=${provider}&${params.toString()}`);
    }

    // Health Check
    async healthCheck() {
        return this.request('/health');
    }

    // WebSocket connection helper
    createWebSocketConnection(endpoint: string): WebSocket {
        const wsUrl = this.gatewayUrl.replace('http', 'ws');
        return new WebSocket(`${wsUrl}${endpoint}`);
    }
}

// Export singleton instance
export const gatewayClient = new GatewayClient();

// Export types for TypeScript
export interface Integration {
    id: number;
    user_id: string;
    provider: string;
    status: string;
    scopes: string[];
    external_user_id?: string;
    external_email?: string;
    external_name?: string;
    has_access_token: boolean;
    has_refresh_token: boolean;
    token_expires_at?: string;
    token_created_at?: string;
    last_sync_at?: string;
    last_error?: string;
    error_count: number;
    created_at: string;
    updated_at: string;
}

export interface IntegrationListResponse {
    integrations: Integration[];
    total: number;
    active_count: number;
    error_count: number;
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

export default gatewayClient; 