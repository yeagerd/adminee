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
}); 