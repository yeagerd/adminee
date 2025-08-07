import { getSession } from 'next-auth/react';
import { GatewayClient } from './gateway-client';

jest.mock('next-auth/react');

const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('GatewayClient', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('attaches JWT as Bearer token in Authorization header if session has accessToken', async () => {
        (getSession as jest.Mock).mockResolvedValue({ accessToken: 'test-jwt-token' });
        mockFetch.mockResolvedValue({
            ok: true,
            headers: { get: () => 'application/json' },
            json: async () => ({ success: true }),
        });

        const client = new GatewayClient();
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

        const client = new GatewayClient();
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

    describe('getPackages with cursor-based pagination', () => {
        const mockPackagesResponse = {
            data: [
                {
                    id: '1',
                    tracking_number: '123456789',
                    carrier: 'fedex',
                    status: 'pending',
                    updated_at: '2024-03-13T10:30:00Z',
                    events_count: 0,
                    labels: []
                }
            ],
            pagination: {
                next_cursor: 'eyJsYXN0X2lkIjoxLCJsYXN0X3VwZGF0ZWRfYXQiOiIyMDI0LTAzLTEzVDEwOjMwOjAwWiIsImZpbHRlcnMiOnt9LCJkaXJlY3Rpb24iOiJuZXh0IiwibGltaXQiOjIwfQ==',
                prev_cursor: null,
                has_next: true,
                has_prev: false,
                limit: 20
            }
        };

        beforeEach(() => {
            (getSession as jest.Mock).mockResolvedValue({ accessToken: 'test-jwt-token' });
            mockFetch.mockResolvedValue({
                ok: true,
                headers: { get: () => 'application/json' },
                json: async () => mockPackagesResponse,
            });
        });

        it('calls getPackages with cursor-based pagination parameters', async () => {
            const client = new GatewayClient();
            const params = {
                cursor: 'test-cursor',
                limit: 10,
                direction: 'next' as const,
                tracking_number: '123456789',
                carrier: 'fedex',
                status: 'pending',
                user_id: 'user123'
            };

            await client.getPackages(params);

            expect(mockFetch).toHaveBeenCalledWith(
                expect.stringContaining('/api/v1/shipments/packages?cursor=test-cursor&limit=10&direction=next&tracking_number=123456789&carrier=fedex&status=pending&user_id=user123'),
                expect.any(Object)
            );
        });

        it('calls getPackages without parameters', async () => {
            const client = new GatewayClient();
            await client.getPackages();

            expect(mockFetch).toHaveBeenCalledWith(
                expect.stringContaining('/api/v1/shipments/packages'),
                expect.any(Object)
            );
        });

        it('returns cursor-based pagination response structure', async () => {
            const client = new GatewayClient();
            const result = await client.getPackages();

            expect(result).toEqual(mockPackagesResponse);
            expect(result).toHaveProperty('next_cursor');
            expect(result).toHaveProperty('prev_cursor');
            expect(result).toHaveProperty('has_next');
            expect(result).toHaveProperty('has_prev');
            expect(result).toHaveProperty('limit');
        });

        it('handles empty pagination response', async () => {
            mockFetch.mockResolvedValue({
                ok: true,
                headers: { get: () => 'application/json' },
                json: async () => ({
                    packages: [],
                    next_cursor: null,
                    prev_cursor: null,
                    has_next: false,
                    has_prev: false,
                    limit: 20
                }),
            });

            const client = new GatewayClient();
            const result = await client.getPackages();

            expect(result.packages).toEqual([]);
            expect(result.has_next).toBe(false);
            expect(result.has_prev).toBe(false);
        });

        it('handles cursor validation errors', async () => {
            mockFetch.mockResolvedValue({
                ok: false,
                status: 400,
                text: async () => JSON.stringify({
                    detail: {
                        error: 'Invalid or expired cursor token',
                        cursor_token: 'invalid-token',
                        reason: 'Token validation failed'
                    }
                }),
            });

            const client = new GatewayClient();
            
            await expect(client.getPackages({ cursor: 'invalid-token' })).rejects.toThrow();
        });
    });
}); 