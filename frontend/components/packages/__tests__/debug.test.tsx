import { render, screen, waitFor } from '@testing-library/react';
import { useRouter, useSearchParams } from 'next/navigation';
import gatewayClient from '../../../lib/gateway-client';

import PackageDashboard from '../PackageDashboard';

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
    useRouter: jest.fn(),
    useSearchParams: jest.fn(),
}));

// Mock the gateway client
jest.mock('../../../lib/gateway-client', () => ({
    __esModule: true,
    default: {
        getPackages: jest.fn(),
        updatePackage: jest.fn(),
        deletePackage: jest.fn(),
        refreshPackage: jest.fn(),
    },
}));

const mockRouter = {
    push: jest.fn(),
    replace: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn(),
    prefetch: jest.fn(),
};

const mockSearchParams = new URLSearchParams();

describe('Debug Test', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        (useRouter as jest.Mock).mockReturnValue(mockRouter);
        (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);
    });

    it('should display packages when they are returned', async () => {
        const mockPackages = [
            {
                id: '1',
                tracking_number: 'TRACK001',
                carrier: 'FedEx',
                status: 'in_transit',
                estimated_delivery: '2025-08-10', // Recent date within 7 days
                updated_at: '2024-01-10T10:00:00Z',
                events_count: 3,
                labels: ['urgent'],
            },
        ];

        const mockPaginationInfo = {
            next_cursor: null,
            prev_cursor: null,
            has_next: false,
            has_prev: false,
            limit: 20,
        };

        const mockResponse = {
            packages: mockPackages,
            ...mockPaginationInfo,
        };

        (gatewayClient.getPackages as jest.Mock).mockResolvedValue(mockResponse);

        render(<PackageDashboard />);

        // Wait for initial load
        await waitFor(() => {
            expect(screen.getByText('TRACK001')).toBeInTheDocument();
        });
    });
}); 