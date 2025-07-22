import { ApiResponse, CalendarEventsResponse, GetEmailsResponse } from '@/types/office-service';
import { getSession } from 'next-auth/react';
import { IntegrationStatus } from './constants';
import { env, validateClientEnv } from './env';

interface GatewayClientOptions {
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
    body?: unknown;
    headers?: Record<string, string>;
}

export class GatewayClient {
    constructor() {
        // Validate client-side environment variables on instantiation
        validateClientEnv();
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

    public async request<T>(endpoint: string, options: GatewayClientOptions = {}): Promise<T> {
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

        const url = `${env.GATEWAY_URL}${endpoint}`;

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
                const errorText = await response.text();
                let errorMessage = `Gateway Error (${response.status}): ${errorText}`;

                // Try to parse JSON error response
                try {
                    const errorJson = JSON.parse(errorText);
                    if (errorJson.message) {
                        errorMessage = errorJson.message;
                    }
                } catch {
                    // If not JSON, use the raw text
                }

                throw new Error(errorMessage);
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

    async chatStream(message: string, threadId?: string, userTimezone?: string, signal?: AbortSignal): Promise<ReadableStream> {
        const session = await getSession();
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
        };

        if (session?.accessToken) {
            headers['Authorization'] = `Bearer ${session.accessToken}`;
        }

        const response = await fetch(`${env.GATEWAY_URL}/api/chat/stream`, {
            method: 'POST',
            headers,
            body: JSON.stringify({
                message,
                thread_id: threadId,
                user_timezone: userTimezone,
            }),
            signal,
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Gateway Stream Error (${response.status}): ${errorText}`);
        }

        return response.body!;
    }

    async getChatHistory(threadId: string) {
        return this.request(`/api/chat/history/${threadId}`);
    }

    async getChatThreads() {
        return this.request('/api/chat/threads');
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
        // Use a dedicated integration callback URL to avoid conflicts with NextAuth
        const redirectUri = `${window.location.origin}/integrations/callback`;

        return this.request('/api/users/me/integrations/oauth/start', {
            method: 'POST',
            body: {
                provider,
                scopes,
                redirect_uri: redirectUri,
            },
        });
    }

    async completeOAuthFlow(provider: string, code: string, state: string): Promise<OAuthCallbackResponse> {
        return this.request<OAuthCallbackResponse>(`/api/users/me/integrations/oauth/callback?provider=${provider}`, {
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
        }>(`/api/users/me/integrations/${provider}/scopes`);
    }

    // Office Service
    async getCalendarEvents(
        providers?: string[],
        limit: number = 50,
        start_date?: string,
        end_date?: string,
        calendar_ids?: string[],
        q?: string,
        time_zone: string = 'UTC'
    ) {
        const params = new URLSearchParams();
        if (providers && providers.length > 0) {
            providers.forEach(provider => params.append('providers', provider));
        }
        params.append('limit', limit.toString());
        if (start_date) params.append('start_date', start_date);
        if (end_date) params.append('end_date', end_date);
        if (calendar_ids && calendar_ids.length > 0) {
            calendar_ids.forEach(id => params.append('calendar_ids', id));
        }
        if (q) params.append('q', q);
        params.append('time_zone', time_zone);

        return this.request<ApiResponse<CalendarEventsResponse>>(`/api/calendar/events?${params.toString()}`);
    }

    async getEmails(
        providers: string[],
        limit?: number,
        offset?: number
    ): Promise<ApiResponse<GetEmailsResponse>> {
        const params = new URLSearchParams();
        if (limit) params.append('limit', limit.toString());
        if (offset) params.append('offset', offset.toString());

        // Add providers as a list
        providers.forEach(provider => {
            params.append('providers', provider);
        });

        return this.request<ApiResponse<GetEmailsResponse>>(`/api/email/messages?${params.toString()}`);
    }

    async getFiles(provider: string, path?: string) {
        const params = new URLSearchParams();
        if (path) params.append('path', path);

        return this.request(`/api/files?provider=${provider}&${params.toString()}`);
    }

    // Draft Management
    async listDrafts(filters?: { type?: string | string[]; status?: string | string[]; search?: string; }): Promise<DraftListResponse> {
        const params = new URLSearchParams();
        if (filters?.type) {
            if (Array.isArray(filters.type)) {
                filters.type.forEach(t => params.append('draft_type', t));
            } else {
                params.append('draft_type', filters.type);
            }
        }
        if (filters?.status) {
            if (Array.isArray(filters.status)) {
                filters.status.forEach(s => params.append('status', s));
            } else {
                params.append('status', filters.status);
            }
        }
        if (filters?.search) params.append('search', filters.search);
        return this.request<DraftListResponse>(`/api/user-drafts?${params.toString()}`);
    }

    async createDraft(draftData: { type: string; content: string; metadata?: Record<string, unknown>; threadId?: string; }): Promise<DraftApiResponse> {
        return this.request<DraftApiResponse>('/api/user-drafts', {
            method: 'POST',
            body: draftData,
        });
    }

    async updateDraft(draftId: string, draftData: { content?: string; metadata?: Record<string, unknown>; status?: string; }): Promise<DraftApiResponse> {
        return this.request<DraftApiResponse>(`/api/user-drafts/${draftId}`, {
            method: 'PUT',
            body: draftData,
        });
    }

    async deleteDraft(draftId: string): Promise<void> {
        return this.request<void>(`/api/user-drafts/${draftId}`, {
            method: 'DELETE',
        });
    }

    async getDraft(draftId: string): Promise<DraftApiResponse> {
        return this.request<DraftApiResponse>(`/api/user-drafts/${draftId}`);
    }

    // Health Check
    async healthCheck() {
        return this.request('/health');
    }

    // WebSocket connection helper
    createWebSocketConnection(endpoint: string): WebSocket {
        const wsUrl = env.GATEWAY_URL.replace('http', 'ws');
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
    status: IntegrationStatus;
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

export interface OAuthCallbackResponse {
    success: boolean;
    integration_id?: number;
    provider: string;
    status: string;
    scopes: string[];
    external_user_info?: Record<string, unknown>;
    error?: string;
}

export interface DraftApiResponse {
    id: string;
    type: string;
    status: string;
    content: string;
    metadata: Record<string, unknown>;
    is_ai_generated?: boolean;
    created_at: string;
    updated_at: string;
    user_id: string;
    thread_id?: string;
}

export interface DraftListResponse {
    drafts: DraftApiResponse[];
    total_count: number;
    has_more: boolean;
}

export default gatewayClient;