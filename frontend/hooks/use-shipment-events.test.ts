import { PACKAGE_STATUS } from '@/lib/package-status';
import { shipmentsClient } from '@/lib/shipments-client';
import { renderHook, waitFor } from '@testing-library/react';
import { useShipmentEvents } from './use-shipment-events';

// Mock the shipments client
jest.mock('@/lib/shipments-client', () => ({
    shipmentsClient: {
        getEventsByEmail: jest.fn(),
    },
}));

const mockShipmentsClient = shipmentsClient as jest.Mocked<typeof shipmentsClient>;

describe('useShipmentEvents', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('should return empty events when emailId is empty', () => {
        const { result } = renderHook(() => useShipmentEvents(''));

        expect(result.current.data).toEqual([]);
        expect(result.current.hasEvents).toBe(false);
        expect(result.current.isLoading).toBe(false);
        expect(result.current.error).toBeNull();
    });

    it('should fetch events when emailId is provided', async () => {
        const mockEvents = [
            {
                id: '1',
                event_date: '2024-01-01T10:00:00Z',
                status: PACKAGE_STATUS.DELIVERED,
                location: 'New York, NY',
                description: 'Package delivered',
                created_at: '2024-01-01T10:00:00Z',
            },
        ];

        mockShipmentsClient.getEventsByEmail.mockResolvedValue(mockEvents);

        const { result } = renderHook(() => useShipmentEvents('test-email-id'));

        // Initially loading
        expect(result.current.isLoading).toBe(true);

        // Wait for the fetch to complete
        await waitFor(() => {
            expect(result.current.isLoading).toBe(false);
        });

        expect(result.current.data).toEqual(mockEvents);
        expect(result.current.hasEvents).toBe(true);
        expect(result.current.error).toBeNull();
        expect(mockShipmentsClient.getEventsByEmail).toHaveBeenCalledWith('test-email-id');
    });

    it('should handle errors when fetch fails', async () => {
        const errorMessage = 'Failed to fetch events';
        mockShipmentsClient.getEventsByEmail.mockRejectedValue(new Error(errorMessage));

        // Mock console.error to avoid logging during this test
        const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

        const { result } = renderHook(() => useShipmentEvents('test-email-id'));

        await waitFor(() => {
            expect(result.current.isLoading).toBe(false);
        });

        expect(result.current.data).toEqual([]);
        expect(result.current.hasEvents).toBe(false);
        expect(result.current.error).toBe(errorMessage);

        // Restore original console.error
        consoleErrorSpy.mockRestore();
    });

    it('should return hasEvents as false when no events are found', async () => {
        mockShipmentsClient.getEventsByEmail.mockResolvedValue([]);

        const { result } = renderHook(() => useShipmentEvents('test-email-id'));

        await waitFor(() => {
            expect(result.current.isLoading).toBe(false);
        });

        expect(result.current.data).toEqual([]);
        expect(result.current.hasEvents).toBe(false);
        expect(result.current.error).toBeNull();
    });
}); 