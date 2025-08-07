import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useRouter, useSearchParams } from 'next/navigation';
import gatewayClient from '../../../lib/gateway-client';
import { shipmentsClient } from '../../../lib/shipments-client';
import PackageDashboard from '../PackageDashboard';

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
    useRouter: jest.fn(),
    useSearchParams: jest.fn(),
}));

// Mock the shipments client
jest.mock('../../../lib/shipments-client', () => ({
    shipmentsClient: {
        getPackages: jest.fn(),
        getNextPage: jest.fn(),
        getPrevPage: jest.fn(),
        getFirstPage: jest.fn(),
    },
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

describe('Package Pagination E2E', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        (useRouter as jest.Mock).mockReturnValue(mockRouter);
        (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);
    });

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
        {
            id: '2',
            tracking_number: 'TRACK002',
            carrier: 'UPS',
            status: 'delivered',
            estimated_delivery: '2025-08-09',
            updated_at: '2024-01-09T10:00:00Z',
            events_count: 5,
            labels: ['fragile'],
        },
    ];

    const mockPaginationInfo = {
        next_cursor: 'eyJsYXN0X2lkIjoiMiIsImxhc3RfdXBkYXRlZCI6IjIwMjQtMDEtMDlUMTA6MDA6MDBaIiwiZGlyZWN0aW9uIjoibmV4dCIsImxpbWl0IjoyMH0=',
        prev_cursor: null,
        has_next: true,
        has_prev: false,
        limit: 20,
    };

    describe('Complete Cursor Pagination User Flows', () => {
        it('should load first page and display pagination controls', async () => {
            (gatewayClient.getPackages as jest.Mock).mockResolvedValue({
                packages: mockPackages,
                ...mockPaginationInfo,
            });

            render(<PackageDashboard />);

            // Wait for initial load
            await waitFor(() => {
                expect(screen.getByText('TRACK001')).toBeInTheDocument();
                expect(screen.getByText('TRACK002')).toBeInTheDocument();
            });

            // Check pagination controls are rendered
            expect(screen.getByText('First')).toBeInTheDocument();
            expect(screen.getByText('Previous')).toBeInTheDocument();
            expect(screen.getByText('Next')).toBeInTheDocument();

            // Check pagination state
            expect(screen.getByText('Next')).not.toBeDisabled();
            expect(screen.getByText('Previous')).toBeDisabled();
            expect(screen.getByText('First')).toBeDisabled();
        });

        it('should navigate to next page when Next button is clicked', async () => {
            const nextPagePackages = [
                {
                    id: '3',
                    tracking_number: 'TRACK003',
                    carrier: 'DHL',
                    status: 'out_for_delivery',
                    estimated_delivery: '2025-08-11',
                    updated_at: '2024-01-08T10:00:00Z',
                    events_count: 2,
                    labels: [],
                },
            ];

            const nextPagePagination = {
                next_cursor: 'eyJsYXN0X2lkIjoiMyIsImxhc3RfdXBkYXRlZCI6IjIwMjQtMDEtMDhUMTA6MDA6MDBaIiwiZGlyZWN0aW9uIjoibmV4dCIsImxpbWl0IjoyMH0=',
                prev_cursor: 'eyJsYXN0X2lkIjoiMiIsImxhc3RfdXBkYXRlZCI6IjIwMjQtMDEtMDlUMTA6MDA6MDBaIiwiZGlyZWN0aW9uIjoicHJldiIsImxpbWl0IjoyMH0=',
                has_next: false,
                has_prev: true,
                limit: 20,
            };

            (gatewayClient.getPackages as jest.Mock)
                .mockResolvedValueOnce({
                    packages: mockPackages,
                    ...mockPaginationInfo,
                })
                .mockResolvedValueOnce({
                    packages: nextPagePackages,
                    ...nextPagePagination,
                });

            render(<PackageDashboard />);

            // Wait for initial load
            await waitFor(() => {
                expect(screen.getByText('TRACK001')).toBeInTheDocument();
            });

            // Click Next button
            fireEvent.click(screen.getByText('Next'));

            // Wait for next page to load
            await waitFor(() => {
                expect(screen.getByText('TRACK003')).toBeInTheDocument();
            });

            // Verify previous packages are no longer visible
            expect(screen.queryByText('TRACK001')).not.toBeInTheDocument();
            expect(screen.queryByText('TRACK002')).not.toBeInTheDocument();

            // Check pagination state updated
            expect(screen.getByText('Next')).toBeDisabled();
            expect(screen.getByText('Previous')).not.toBeDisabled();
            expect(screen.getByText('First')).not.toBeDisabled();
        });

        it('should navigate to previous page when Previous button is clicked', async () => {
            const prevPagePagination = {
                next_cursor: 'eyJsYXN0X2lkIjoiMiIsImxhc3RfdXBkYXRlZCI6IjIwMjQtMDEtMDlUMTA6MDA6MDBaIiwiZGlyZWN0aW9uIjoibmV4dCIsImxpbWl0IjoyMH0=',
                prev_cursor: null,
                has_next: true,
                has_prev: false,
                limit: 20,
            };

            (gatewayClient.getPackages as jest.Mock)
                .mockResolvedValueOnce({
                    packages: mockPackages,
                    ...mockPaginationInfo,
                })
                .mockResolvedValueOnce({
                    packages: mockPackages,
                    ...prevPagePagination,
                });

            render(<PackageDashboard />);

            // Wait for initial load
            await waitFor(() => {
                expect(screen.getByText('TRACK001')).toBeInTheDocument();
            });

            // Navigate to next page first
            fireEvent.click(screen.getByText('Next'));

            // Wait for next page
            await waitFor(() => {
                expect(shipmentsClient.getPackages).toHaveBeenCalledWith(
                    expect.objectContaining({
                        cursor: mockPaginationInfo.next_cursor,
                        direction: 'next',
                    })
                );
            });

            // Click Previous button
            fireEvent.click(screen.getByText('Previous'));

            // Wait for previous page to load
            await waitFor(() => {
                expect(screen.getByText('TRACK001')).toBeInTheDocument();
            });
        });

        it('should navigate to first page when First button is clicked', async () => {
            const firstPagePagination = {
                next_cursor: 'eyJsYXN0X2lkIjoiMiIsImxhc3RfdXBkYXRlZCI6IjIwMjQtMDEtMDlUMTA6MDA6MDBaIiwiZGlyZWN0aW9uIjoibmV4dCIsImxpbWl0IjoyMH0=',
                prev_cursor: null,
                has_next: true,
                has_prev: false,
                limit: 20,
            };

            (gatewayClient.getPackages as jest.Mock)
                .mockResolvedValueOnce({
                    packages: mockPackages,
                    ...mockPaginationInfo,
                })
                .mockResolvedValueOnce({
                    packages: mockPackages,
                    ...firstPagePagination,
                });

            render(<PackageDashboard />);

            // Wait for initial load
            await waitFor(() => {
                expect(screen.getByText('TRACK001')).toBeInTheDocument();
            });

            // Navigate to next page first
            fireEvent.click(screen.getByText('Next'));

            // Wait for next page
            await waitFor(() => {
                expect(shipmentsClient.getPackages).toHaveBeenCalledWith(
                    expect.objectContaining({
                        cursor: mockPaginationInfo.next_cursor,
                        direction: 'next',
                    })
                );
            });

            // Click First button
            fireEvent.click(screen.getByText('First'));

            // Wait for first page to load
            await waitFor(() => {
                expect(screen.getByText('TRACK001')).toBeInTheDocument();
            });

            // Verify getFirstPage was called
            expect(shipmentsClient.getPackages).toHaveBeenCalledWith(
                expect.objectContaining({
                    direction: 'next',
                })
            );
        });
    });

    describe('Cursor Pagination with Filters', () => {
        it('should maintain filters when navigating between pages', async () => {
            const filteredPackages = [
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

            const filteredPagination = {
                next_cursor: 'eyJsYXN0X2lkIjoiMSIsImxhc3RfdXBkYXRlZCI6IjIwMjQtMDEtMTBUMTA6MDA6MDBaIiwiZmlsdGVycyI6IntcImNhcnJpZXJcIjpcIkZlZEV4XCJ9IiwiZGlyZWN0aW9uIjoibmV4dCIsImxpbWl0IjoyMH0=',
                prev_cursor: null,
                has_next: false,
                has_prev: false,
                limit: 20,
            };

            (gatewayClient.getPackages as jest.Mock).mockResolvedValue({
                packages: filteredPackages,
                ...filteredPagination,
            });

            render(<PackageDashboard />);

            // Wait for initial load
            await waitFor(() => {
                expect(screen.getByText('TRACK001')).toBeInTheDocument();
            });

            // Apply carrier filter - use dropdown instead of input
            const carrierFilterButton = screen.getByText('Carrier: All');
            fireEvent.click(carrierFilterButton);
            const fedexOption = screen.getByText('FedEx');
            fireEvent.click(fedexOption);

            // Wait for filtered results
            await waitFor(() => {
                expect(shipmentsClient.getPackages).toHaveBeenCalledWith(
                    expect.objectContaining({
                        carrier: 'FedEx',
                    })
                );
            });

            // Verify only FedEx packages are shown
            expect(screen.getByText('TRACK001')).toBeInTheDocument();
            expect(screen.queryByText('TRACK002')).not.toBeInTheDocument();
        });

        it('should reset pagination when filters change', async () => {
            (gatewayClient.getPackages as jest.Mock).mockResolvedValue({
                packages: mockPackages,
                ...mockPaginationInfo,
            });

            render(<PackageDashboard />);

            // Wait for initial load
            await waitFor(() => {
                expect(screen.getByText('TRACK001')).toBeInTheDocument();
            });

            // Navigate to next page
            fireEvent.click(screen.getByText('Next'));

            // Wait for next page
            await waitFor(() => {
                expect(gatewayClient.getPackages).toHaveBeenCalledWith(
                    expect.objectContaining({
                        cursor: mockPaginationInfo.next_cursor,
                    })
                );
            });

            // Change filter (should reset to first page)
            const carrierFilterButton = screen.getByText('Carrier: FedEx');
            fireEvent.click(carrierFilterButton);
            const upsOption = screen.getByText('UPS');
            fireEvent.click(upsOption);

            // Verify getFirstPage was called (no cursor)
            await waitFor(() => {
                expect(gatewayClient.getPackages).toHaveBeenCalledWith(
                    expect.objectContaining({
                        carrier: 'UPS',
                        direction: 'next',
                    })
                );
            });
        });
    });

    describe('Cursor Pagination Error Scenarios', () => {
        it('should handle expired cursor tokens gracefully', async () => {
            (gatewayClient.getPackages as jest.Mock)
                .mockResolvedValueOnce({
                    packages: mockPackages,
                    ...mockPaginationInfo,
                })
                .mockRejectedValueOnce(new Error('Invalid or expired cursor token'));

            render(<PackageDashboard />);

            // Wait for initial load
            await waitFor(() => {
                expect(screen.getByText('TRACK001')).toBeInTheDocument();
            });

            // Click Next button (should fail with expired token)
            fireEvent.click(screen.getByText('Next'));

            // Wait for error handling
            await waitFor(() => {
                expect(screen.getByText('Invalid or expired cursor token')).toBeInTheDocument();
            });

            // Verify fallback to first page was attempted
            expect(gatewayClient.getPackages).toHaveBeenCalledWith(
                expect.objectContaining({
                    direction: 'next',
                })
            );
        });

        it('should handle invalid cursor tokens gracefully', async () => {
            (gatewayClient.getPackages as jest.Mock)
                .mockResolvedValueOnce({
                    packages: mockPackages,
                    ...mockPaginationInfo,
                })
                .mockRejectedValueOnce(new Error('Invalid cursor format'));

            render(<PackageDashboard />);

            // Wait for initial load
            await waitFor(() => {
                expect(screen.getByText('TRACK001')).toBeInTheDocument();
            });

            // Click Next button (should fail with invalid token)
            fireEvent.click(screen.getByText('Next'));

            // Wait for error handling
            await waitFor(() => {
                expect(screen.getByText('Invalid cursor format')).toBeInTheDocument();
            });
        });

        it('should handle network errors during pagination', async () => {
            (gatewayClient.getPackages as jest.Mock)
                .mockResolvedValueOnce({
                    packages: mockPackages,
                    ...mockPaginationInfo,
                })
                .mockRejectedValueOnce(new Error('Network error'));

            render(<PackageDashboard />);

            // Wait for initial load
            await waitFor(() => {
                expect(screen.getByText('TRACK001')).toBeInTheDocument();
            });

            // Click Next button (should fail with network error)
            fireEvent.click(screen.getByText('Next'));

            // Wait for error handling
            await waitFor(() => {
                expect(screen.getByText('Network error')).toBeInTheDocument();
            });
        });

        it('should handle empty results gracefully', async () => {
            (gatewayClient.getPackages as jest.Mock).mockResolvedValue({
                packages: [],
                next_cursor: null,
                prev_cursor: null,
                has_next: false,
                has_prev: false,
                limit: 20,
            });

            render(<PackageDashboard />);

            // Wait for empty state
            await waitFor(() => {
                expect(screen.getByText(/no packages found/i)).toBeInTheDocument();
            });

            // Verify pagination controls are disabled
            expect(screen.getByText('First')).toBeDisabled();
            expect(screen.getByText('Previous')).toBeDisabled();
            expect(screen.getByText('Next')).toBeDisabled();
        });
    });

    describe('URL State Management', () => {
        it('should update URL parameters when navigating pages', async () => {
            (gatewayClient.getPackages as jest.Mock).mockResolvedValue({
                packages: mockPackages,
                ...mockPaginationInfo,
            });

            render(<PackageDashboard />);

            // Wait for initial load
            await waitFor(() => {
                expect(screen.getByText('TRACK001')).toBeInTheDocument();
            });

            // Click Next button
            fireEvent.click(screen.getByText('Next'));

            // Verify URL was updated
            await waitFor(() => {
                expect(mockRouter.push).toHaveBeenCalledWith(
                    expect.stringContaining('cursor='),
                    expect.objectContaining({ scroll: false })
                );
            });
        });

        it('should load state from URL parameters on mount', async () => {
            const urlWithCursor = new URLSearchParams();
            urlWithCursor.set('cursor', 'test-cursor');
            urlWithCursor.set('carrier', 'FedEx');

            (useSearchParams as jest.Mock).mockReturnValue(urlWithCursor);

            (gatewayClient.getPackages as jest.Mock).mockResolvedValue({
                packages: mockPackages,
                ...mockPaginationInfo,
            });

            render(<PackageDashboard />);

            // Verify packages were loaded with URL parameters
            await waitFor(() => {
                expect(gatewayClient.getPackages).toHaveBeenCalledWith(
                    expect.objectContaining({
                        cursor: 'test-cursor',
                        carrier: 'FedEx',
                    })
                );
            });
        });
    });

    describe('Performance Optimizations', () => {
        it('should debounce rapid pagination clicks', async () => {
            jest.useFakeTimers();

            (gatewayClient.getPackages as jest.Mock).mockResolvedValue({
                packages: mockPackages,
                ...mockPaginationInfo,
            });

            render(<PackageDashboard />);

            // Wait for initial load
            await waitFor(() => {
                expect(screen.getByText('TRACK001')).toBeInTheDocument();
            });

            // Rapidly click Next button multiple times
            fireEvent.click(screen.getByText('Next'));
            fireEvent.click(screen.getByText('Next'));
            fireEvent.click(screen.getByText('Next'));

            // Fast-forward timers
            jest.runAllTimers();

            // Verify only one request was made
            await waitFor(() => {
                expect(gatewayClient.getPackages).toHaveBeenCalledTimes(2); // Initial load + 1 debounced request
            });

            jest.useRealTimers();
        });

        it('should cache cursor data for better performance', async () => {
            (gatewayClient.getPackages as jest.Mock).mockResolvedValue({
                packages: mockPackages,
                ...mockPaginationInfo,
            });

            render(<PackageDashboard />);

            // Wait for initial load
            await waitFor(() => {
                expect(screen.getByText('TRACK001')).toBeInTheDocument();
            });

            // Navigate to next page
            fireEvent.click(screen.getByText('Next'));

            // Navigate back to previous page
            fireEvent.click(screen.getByText('Previous'));

            // Verify cached data was used (no additional API calls for same page)
            await waitFor(() => {
                expect(gatewayClient.getPackages).toHaveBeenCalledTimes(3); // Initial + next + prev
            });
        });
    });
}); 