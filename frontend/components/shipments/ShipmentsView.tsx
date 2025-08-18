import { shipmentsApi } from '@/api';
import type { PackageOut } from '@/types/api/shipments';
import { usePagination } from '@/hooks/use-pagination';
import { PackageStatus } from '@/types/api/shipments';
import { useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import ShipmentDetailsModal from './ShipmentDetailsModal';
import ShipmentsList, { ShipmentItem } from './ShipmentsList';

interface ShipmentsViewProps {
    className?: string;
}

export default function ShipmentsView({ className = "" }: ShipmentsViewProps) {
    const router = useRouter();
    const searchParams = useSearchParams();

    const [shipments, setShipments] = useState<ShipmentItem[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Filter states
    const [carrierFilter, setCarrierFilter] = useState<string>('');
    const [statusFilter, setStatusFilter] = useState<string>('');
    const [searchTerm, setSearchTerm] = useState<string>('');

    // Modal states
    const [selectedShipment, setSelectedShipment] = useState<PackageOut | null>(null);
    const [isModalOpen, setIsModalOpen] = useState(false);

    // Pagination hook
    const {
        paginationState,
        paginationHandlers,
        setPaginationData,
        setLoading: setPaginationLoading,
        resetPagination,
    } = usePagination({
        initialLimit: 20,
        onPageChange: handlePageChange,
    });

    // Load shipments data
    const loadShipments = useCallback(async (cursor?: string, direction: 'next' | 'prev' | 'first' = 'next') => {
        setLoading(true);
        setError(null);

        try {
            const filters: Record<string, string> = {};
            if (carrierFilter) filters.carrier = carrierFilter;
            if (statusFilter) filters.status = statusFilter;

            let response;
            if (direction === 'first' || !cursor) {
                response = await shipmentsApi.getFirstPage(20, filters);
            } else {
                response = await shipmentsApi.getPackages({
                    cursor,
                    limit: 20,
                    direction,
                    ...filters,
                });
            }

            // Transform PackageOut to ShipmentItem
            const transformedShipments: ShipmentItem[] = response.packages.map((pkg: PackageOut) => ({
                id: pkg.id,
                tracking_number: pkg.tracking_number,
                carrier: pkg.carrier,
                status: pkg.status,
                estimated_delivery: pkg.estimated_delivery || undefined,
                actual_delivery: pkg.actual_delivery || undefined,
                recipient_name: pkg.recipient_name || undefined,
                package_description: pkg.package_description || undefined,
                tracking_link: pkg.tracking_link || undefined,
                updated_at: pkg.updated_at,
                events_count: pkg.events_count,
                labels: pkg.labels || [],
            }));

            setShipments(transformedShipments);

            // Update pagination state
            setPaginationData({
                hasNext: response.has_next,
                hasPrev: response.has_prev,
                nextCursor: response.next_cursor,
                prevCursor: response.prev_cursor,
                itemsCount: transformedShipments.length,
            });

            // Update URL with cursor
            if (cursor && direction !== 'first') {
                const newSearchParams = new URLSearchParams(searchParams.toString());
                newSearchParams.set('cursor', cursor);
                const newURL = `${window.location.pathname}?${newSearchParams.toString()}`;
                router.push(newURL, { scroll: false });
            }

        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to load shipments';
            setError(errorMessage);
            console.error('Error loading shipments:', err);
        } finally {
            setLoading(false);
            setPaginationLoading(false);
        }
    }, [carrierFilter, statusFilter, searchParams, router, setPaginationData, setPaginationLoading]);

    // Handle page changes
    function handlePageChange(cursor: string | null, direction: 'next' | 'prev' | 'first') {
        loadShipments(cursor || undefined, direction);
    }

    // Handle filters
    const handleFilterChange = useCallback(() => {
        resetPagination();
        loadShipments(undefined, 'first');
    }, [resetPagination, loadShipments]);

    // Handle search
    const handleSearch = useCallback(() => {
        resetPagination();
        loadShipments(undefined, 'first');
    }, [resetPagination, loadShipments]);

    // Load initial data
    useEffect(() => {
        const cursor = searchParams.get('cursor');
        if (cursor) {
            loadShipments(cursor, 'next');
        } else {
            loadShipments(undefined, 'first');
        }
    }, [loadShipments, searchParams]);

    // Handle filter changes
    useEffect(() => {
        handleFilterChange();
    }, [handleFilterChange]);

    const handleRowClick = (shipment: ShipmentItem) => {
        // Convert ShipmentItem to PackageOut for the modal
        const packageResponse: PackageOut = {
            id: shipment.id,
            tracking_number: shipment.tracking_number,
            carrier: shipment.carrier,
            status: shipment.status as PackageStatus, // Type assertion needed due to interface differences
            estimated_delivery: shipment.estimated_delivery || null,
            actual_delivery: shipment.actual_delivery || null,
            recipient_name: shipment.recipient_name || null,
            shipper_name: null, // Not available in ShipmentItem
            package_description: shipment.package_description || null,
            order_number: null, // Not available in ShipmentItem
            tracking_link: shipment.tracking_link || null,
            updated_at: shipment.updated_at,
            events_count: shipment.events_count || 0,
                            labels: shipment.labels?.map(label => typeof label === 'string' ? { name: label } : label) || [],
        };

        setSelectedShipment(packageResponse);
        setIsModalOpen(true);
    };

    const handleViewDetails = (shipment: ShipmentItem) => {
        // Same as handleRowClick - open the modal
        handleRowClick(shipment);
    };

    const handleTrackPackage = (shipment: ShipmentItem) => {
        // Handle track package
        console.log('Track package:', shipment);
    };

    const handleSort = (field: string) => {
        // Handle sorting - would need to be implemented with the API
        console.log('Sort by:', field);
    };

    const handleCloseModal = () => {
        setIsModalOpen(false);
        setSelectedShipment(null);
    };

    const handleShipmentUpdated = (updatedShipment: PackageOut) => {
        // Update the shipment in the local state
        setShipments(prevShipments =>
            prevShipments.map(shipment =>
                shipment.id === updatedShipment.id
                                            ? {
                            ...shipment,
                            tracking_number: updatedShipment.tracking_number,
                            carrier: updatedShipment.carrier,
                            status: updatedShipment.status,
                            estimated_delivery: updatedShipment.estimated_delivery || undefined,
                            actual_delivery: updatedShipment.actual_delivery || undefined,
                            recipient_name: updatedShipment.recipient_name || undefined,
                            package_description: updatedShipment.package_description || undefined,
                            tracking_link: updatedShipment.tracking_link || undefined,
                            updated_at: updatedShipment.updated_at,
                            events_count: updatedShipment.events_count,
                            labels: updatedShipment.labels || [],
                        }
                    : shipment
            )
        );
    };

    return (
        <div className={`space-y-6 ${className}`}>
            {/* Header */}
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold">Shipments</h1>
                <Button onClick={() => loadShipments(undefined, 'first')} disabled={loading}>
                    Refresh
                </Button>
            </div>

            {/* Filters */}
            <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
                <div className="flex-1">
                    <Input
                        placeholder="Search tracking numbers..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                    />
                </div>

                <Select value={carrierFilter} onValueChange={setCarrierFilter}>
                    <SelectTrigger className="w-32">
                        <SelectValue placeholder="Carrier" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="">All Carriers</SelectItem>
                        <SelectItem value="fedex">FedEx</SelectItem>
                        <SelectItem value="ups">UPS</SelectItem>
                        <SelectItem value="usps">USPS</SelectItem>
                        <SelectItem value="dhl">DHL</SelectItem>
                    </SelectContent>
                </Select>

                <Select value={statusFilter} onValueChange={setStatusFilter}>
                    <SelectTrigger className="w-32">
                        <SelectValue placeholder="Status" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="">All Status</SelectItem>
                        <SelectItem value="pending">Pending</SelectItem>
                        <SelectItem value="in_transit">In Transit</SelectItem>
                        <SelectItem value="delivered">Delivered</SelectItem>
                        <SelectItem value="delayed">Delayed</SelectItem>
                    </SelectContent>
                </Select>
            </div>

            {/* Error Display */}
            {error && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
                    {error}
                </div>
            )}

            {/* Shipments List */}
            <ShipmentsList
                shipments={shipments}
                pagination={paginationState}
                onNextPage={paginationHandlers.onNextPage}
                onPrevPage={paginationHandlers.onPrevPage}
                onFirstPage={paginationHandlers.onFirstPage}
                onSort={handleSort}
                onRowClick={handleRowClick}
                onViewDetails={handleViewDetails}
                onTrackPackage={handleTrackPackage}
                emptyMessage="No shipments found."
                loadingMessage="Loading shipments..."
            />

            {/* Shipment Details Modal */}
            {selectedShipment && (
                <ShipmentDetailsModal
                    isOpen={isModalOpen}
                    onClose={handleCloseModal}
                    shipment={selectedShipment}
                    onShipmentUpdated={handleShipmentUpdated}
                />
            )}
        </div>
    );
}
