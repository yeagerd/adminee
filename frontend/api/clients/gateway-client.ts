import { getSession } from 'next-auth/react';
import { env, validateClientEnv } from '../../lib/env';

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

    private toIsoIfDateOnly(value?: string): string | undefined {
        if (value === undefined) return undefined;
        if (value.includes('T')) return value;
        const parsed = new Date(value);
        return Number.isNaN(parsed.getTime()) ? value : parsed.toISOString();
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
            if (process.env.NODE_ENV !== 'test') {
                // eslint-disable-next-line no-console
                console.error('Gateway Client Error:', error);
            }
            throw error;
        }
    }

    // WebSocket connection helper
    createWebSocketConnection(endpoint: string): WebSocket {
        const wsUrl = env.GATEWAY_URL.replace('http', 'ws');
        return new WebSocket(`${wsUrl}${endpoint}`);
    }

    // Health Check
    async healthCheck() {
        return this.request('/health');
    }

    // Helper method for date normalization
    protected normalizeDate(value?: string): string | undefined {
        return this.toIsoIfDateOnly(value);
    }
}
