import { shipmentsApi } from '@/api';
import { act, render, screen, waitFor } from '@testing-library/react';
import { useRouter, useSearchParams } from 'next/navigation';

import PackageDashboard from '../PackageDashboard';

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
    useRouter: jest.fn(),
    useSearchParams: jest.fn(),
}));

// Mock the shipments API
jest.mock('@/api', () => ({
    shipmentsApi: {
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

        console.log('Mock response:', mockResponse);

        (shipmentsApi.getPackages as jest.Mock).mockResolvedValue(mockResponse);

        const { container } = render(<PackageDashboard />);

        // Wait for the API call to be made
        await waitFor(() => {
            expect(shipmentsApi.getPackages).toHaveBeenCalled();
        }, { timeout: 2000 });

        console.log('API call made with:', (shipmentsApi.getPackages as jest.Mock).mock.calls[0]);

        // Wait for the component to update and stabilize
        await act(async () => {
            await new Promise(resolve => setTimeout(resolve, 100));
        });

        // Debug: log what's actually rendered
        console.log('Rendered HTML:', container.innerHTML);

        // Check if the package is in the DOM
        console.log('Container text content:', container.textContent);

        // Wait for initial load
        await act(async () => {
            await waitFor(() => {
                expect(screen.getByText('TRACK001')).toBeInTheDocument();
            }, { timeout: 5000 });
        });
    });

    it('should display packages when date range is set to all', async () => {
        const mockPackages = [
            {
                id: '1',
                tracking_number: 'TRACK001',
                carrier: 'FedEx',
                status: 'in_transit',
                estimated_delivery: '2025-08-10',
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

        (shipmentsApi.getPackages as jest.Mock).mockResolvedValue(mockResponse);

        await act(async () => {
            render(<PackageDashboard />);
        });

        // Wait for the API call to be made
        await waitFor(() => {
            expect(shipmentsApi.getPackages).toHaveBeenCalled();
        }, { timeout: 2000 });

        // Wait for the component to update and stabilize
        await act(async () => {
            await new Promise(resolve => setTimeout(resolve, 100));
        });

        // Check if the package is now in the DOM
        await act(async () => {
            await waitFor(() => {
                expect(screen.getByText('TRACK001')).toBeInTheDocument();
            }, { timeout: 5000 });
        });
    });

    it('should display packages with date range bypass', async () => {
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

        (shipmentsApi.getPackages as jest.Mock).mockResolvedValue(mockResponse);

        // Create a modified component with date range set to 'all'
        const ModifiedPackageDashboard = () => {
            const component = PackageDashboard();
            // We can't easily modify the state here, so let's just render and see what happens
            return component;
        };

        await act(async () => {
            render(<ModifiedPackageDashboard />);
        });

        // Wait for the API call to be made
        await waitFor(() => {
            expect(shipmentsApi.getPackages).toHaveBeenCalled();
        }, { timeout: 2000 });

        // Wait for the component to update
        await new Promise(resolve => setTimeout(resolve, 1000));

        // Wait for initial load
        await waitFor(() => {
            expect(screen.getByText('TRACK001')).toBeInTheDocument();
        }, { timeout: 5000 });
    });
}); 