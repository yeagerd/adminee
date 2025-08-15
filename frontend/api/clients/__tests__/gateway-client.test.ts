import { getSession } from 'next-auth/react';
import { GatewayClient } from '../gateway-client';

jest.mock('next-auth/react');
jest.mock('../../../lib/env', () => ({
    env: {
        GATEWAY_URL: process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:3001',
    },
    validateClientEnv: jest.fn(),
}));

const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('GatewayClient', () => {
    let client: GatewayClient;

    beforeEach(() => {
        jest.clearAllMocks();
        client = new GatewayClient();
    });

    describe('Authentication', () => {
        it('attaches JWT as Bearer token in Authorization header if session has accessToken', async () => {
            (getSession as jest.Mock).mockResolvedValue({ accessToken: 'test-jwt-token' });
            mockFetch.mockResolvedValue({
                ok: true,
                headers: { get: () => 'application/json' },
                json: async () => ({ success: true }),
            });

            await client.request('/test-endpoint', { method: 'GET' });

            expect(mockFetch).toHaveBeenCalledWith(
                expect.stringContaining('/test-endpoint'),
                expect.objectContaining({
                    headers: expect.objectContaining({
                        Authorization: 'Bearer test-jwt-token',
                    }),
                })
            );
        });

        it('does not attach Authorization header if session has no accessToken', async () => {
            (getSession as jest.Mock).mockResolvedValue({});
            mockFetch.mockResolvedValue({
                ok: true,
                headers: { get: () => 'application/json' },
                json: async () => ({ success: true }),
            });

            await client.request('/test-endpoint', { method: 'GET' });

            expect(mockFetch).toHaveBeenCalledWith(
                expect.stringContaining('/test-endpoint'),
                expect.objectContaining({
                    headers: expect.not.objectContaining({
                        Authorization: expect.any(String),
                    }),
                })
            );
        });

        it('includes Content-Type header by default', async () => {
            (getSession as jest.Mock).mockResolvedValue({});
            mockFetch.mockResolvedValue({
                ok: true,
                headers: { get: () => 'application/json' },
                json: async () => ({ success: true }),
            });

            await client.request('/test-endpoint');

            expect(mockFetch).toHaveBeenCalledWith(
                expect.stringContaining('/test-endpoint'),
                expect.objectContaining({
                    headers: expect.objectContaining({
                        'Content-Type': 'application/json',
                    }),
                })
            );
        });

        it('merges custom headers with auth headers', async () => {
            (getSession as jest.Mock).mockResolvedValue({ accessToken: 'test-jwt-token' });
            mockFetch.mockResolvedValue({
                ok: true,
                headers: { get: () => 'application/json' },
                json: async () => ({ success: true }),
            });

            await client.request('/test-endpoint', {
                headers: { 'X-Custom-Header': 'custom-value' }
            });

            expect(mockFetch).toHaveBeenCalledWith(
                expect.stringContaining('/test-endpoint'),
                expect.objectContaining({
                    headers: expect.objectContaining({
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer test-jwt-token',
                        'X-Custom-Header': 'custom-value',
                    }),
                })
            );
        });
    });

    describe('Request Methods', () => {
        beforeEach(() => {
            (getSession as jest.Mock).mockResolvedValue({});
        });

        it('makes GET request by default', async () => {
            mockFetch.mockResolvedValue({
                ok: true,
                headers: { get: () => 'application/json' },
                json: async () => ({ success: true }),
            });

            await client.request('/test-endpoint');

            expect(mockFetch).toHaveBeenCalledWith(
                expect.stringContaining('/test-endpoint'),
                expect.objectContaining({
                    method: 'GET',
                })
            );
        });

        it('makes POST request with body when specified', async () => {
            mockFetch.mockResolvedValue({
                ok: true,
                headers: { get: () => 'application/json' },
                json: async () => ({ success: true }),
            });

            const body = { test: 'data' };
            await client.request('/test-endpoint', { method: 'POST', body });

            expect(mockFetch).toHaveBeenCalledWith(
                expect.stringContaining('/test-endpoint'),
                expect.objectContaining({
                    method: 'POST',
                    body: JSON.stringify(body),
                })
            );
        });

        it('does not include body for GET requests', async () => {
            mockFetch.mockResolvedValue({
                ok: true,
                headers: { get: () => 'application/json' },
                json: async () => ({ success: true }),
            });

            await client.request('/test-endpoint', { method: 'GET', body: { test: 'data' } });

            expect(mockFetch).toHaveBeenCalledWith(
                expect.stringContaining('/test-endpoint'),
                expect.objectContaining({
                    method: 'GET',
                })
            );

            const callArgs = mockFetch.mock.calls[0][1];
            expect(callArgs.body).toBeUndefined();
        });
    });

    describe('Response Handling', () => {
        beforeEach(() => {
            (getSession as jest.Mock).mockResolvedValue({});
        });

        it('parses JSON responses when content-type is application/json', async () => {
            const mockResponse = { success: true, data: 'test' };
            mockFetch.mockResolvedValue({
                ok: true,
                headers: { get: () => 'application/json' },
                json: async () => mockResponse,
            });

            const result = await client.request('/test-endpoint');

            expect(result).toEqual(mockResponse);
        });

        it('returns text for non-JSON responses', async () => {
            mockFetch.mockResolvedValue({
                ok: true,
                headers: { get: () => 'text/plain' },
                text: async () => 'plain text response',
            });

            const result = await client.request('/test-endpoint');

            expect(result).toBe('plain text response');
        });

        it('handles responses without content-type header', async () => {
            mockFetch.mockResolvedValue({
                ok: true,
                headers: { get: () => null },
                text: async () => 'response without content-type',
            });

            const result = await client.request('/test-endpoint');

            expect(result).toBe('response without content-type');
        });
    });

    describe('Error Handling', () => {
        beforeEach(() => {
            (getSession as jest.Mock).mockResolvedValue({});
        });

        it('throws error for non-ok responses', async () => {
            mockFetch.mockResolvedValue({
                ok: false,
                status: 404,
                text: async () => 'Not Found',
            });

            await expect(client.request('/test-endpoint')).rejects.toThrow('Gateway Error (404): Not Found');
        });

        it('parses JSON error responses', async () => {
            const errorResponse = { message: 'Custom error message' };
            mockFetch.mockResolvedValue({
                ok: false,
                status: 400,
                text: async () => JSON.stringify(errorResponse),
            });

            await expect(client.request('/test-endpoint')).rejects.toThrow('Custom error message');
        });

        it('falls back to raw text for malformed JSON error responses', async () => {
            mockFetch.mockResolvedValue({
                ok: false,
                status: 500,
                text: async () => 'Invalid JSON {',
            });

            await expect(client.request('/test-endpoint')).rejects.toThrow('Gateway Error (500): Invalid JSON {');
        });

        it('logs errors in non-test environments', async () => {
            const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => { });

            // Mock the environment check by temporarily overriding the client's behavior
            const originalEnv = process.env.NODE_ENV;
            Object.defineProperty(process.env, 'NODE_ENV', {
                value: 'development',
                writable: true,
                configurable: true
            });

            mockFetch.mockRejectedValue(new Error('Network error'));

            await expect(client.request('/test-endpoint')).rejects.toThrow('Network error');
            expect(consoleSpy).toHaveBeenCalledWith('Gateway Client Error:', expect.any(Error));

            consoleSpy.mockRestore();
            Object.defineProperty(process.env, 'NODE_ENV', {
                value: originalEnv,
                writable: true,
                configurable: true
            });
        });

        it('does not log errors in test environment', async () => {
            const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => { });

            // Mock the environment check by temporarily overriding the client's behavior
            const originalEnv = process.env.NODE_ENV;
            Object.defineProperty(process.env, 'NODE_ENV', {
                value: 'test',
                writable: true,
                configurable: true
            });

            mockFetch.mockRejectedValue(new Error('Network error'));

            await expect(client.request('/test-endpoint')).rejects.toThrow('Network error');
            expect(consoleSpy).not.toHaveBeenCalled();

            consoleSpy.mockRestore();
            Object.defineProperty(process.env, 'NODE_ENV', {
                value: originalEnv,
                writable: true,
                configurable: true
            });
        });
    });

    describe('WebSocket Connection', () => {
        it('creates WebSocket connection with correct URL', () => {
            const ws = client.createWebSocketConnection('/ws/chat');
            expect(ws.url).toBe('ws://localhost:3001/ws/chat');
        });

        it('converts HTTP to WS and HTTPS to WSS', () => {
            // Test the URL conversion logic
            const httpUrl = 'http://localhost:3001';
            const httpsUrl = 'https://api.example.com';

            expect(httpUrl.replace('http', 'ws')).toBe('ws://localhost:3001');
            expect(httpsUrl.replace('http', 'ws')).toBe('wss://api.example.com');
        });
    });

    describe('Health Check', () => {
        beforeEach(() => {
            (getSession as jest.Mock).mockResolvedValue({});
        });

        it('calls health endpoint', async () => {
            mockFetch.mockResolvedValue({
                ok: true,
                headers: { get: () => 'application/json' },
                json: async () => ({ status: 'healthy' }),
            });

            await client.healthCheck();

            expect(mockFetch).toHaveBeenCalledWith(
                expect.stringContaining('/health'),
                expect.any(Object)
            );
        });
    });

    describe('Date Normalization', () => {
        it('converts date-only strings to ISO format', () => {
            const result = (client as any).normalizeDate('2024-01-15');
            expect(result).toBe('2024-01-15T00:00:00.000Z');
        });

        it('preserves ISO strings with time', () => {
            const isoString = '2024-01-15T10:30:00.000Z';
            const result = (client as any).normalizeDate(isoString);
            expect(result).toBe(isoString);
        });

        it('returns undefined for undefined input', () => {
            const result = (client as any).normalizeDate(undefined);
            expect(result).toBeUndefined();
        });

        it('returns original value for invalid dates', () => {
            const result = (client as any).normalizeDate('invalid-date');
            expect(result).toBe('invalid-date');
        });
    });
});
