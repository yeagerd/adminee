import { Calendar, ExternalLink, Package, Truck } from 'lucide-react';
import { memo } from 'react';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import PaginatedDataTable, { ColumnDefinition } from '../ui/paginated-data-table';
import { TableCell } from '../ui/table';

// Generic shipment interface that could be extended for different types
export interface ShipmentItem {
    id: string;
    tracking_number: string;
    carrier: string;
    status: string;
    estimated_delivery?: string;
    actual_delivery?: string;
    recipient_name?: string;
    package_description?: string;
    tracking_link?: string;
    updated_at: string;
    events_count?: number;
    labels?: string[];
}

interface ShipmentsListProps {
    shipments: ShipmentItem[];
    columns?: ColumnDefinition<ShipmentItem>[];
    pagination?: {
        hasNext: boolean;
        hasPrev: boolean;
        nextCursor?: string;
        prevCursor?: string;
        loading: boolean;
    };
    onNextPage?: () => void;
    onPrevPage?: () => void;
    onFirstPage?: () => void;
    onSort?: (field: string) => void;
    onRowClick?: (shipment: ShipmentItem) => void;
    onViewDetails?: (shipment: ShipmentItem) => void;
    onTrackPackage?: (shipment: ShipmentItem) => void;
    emptyMessage?: string;
    loadingMessage?: string;
    className?: string;
}

const ShipmentsList = memo(function ShipmentsList({
    shipments,
    columns,
    pagination,
    onNextPage,
    onPrevPage,
    onFirstPage,
    onSort,
    onRowClick,
    onViewDetails,
    onTrackPackage,
    emptyMessage = "No shipments found.",
    loadingMessage = "Loading shipments...",
    className = "",
}: ShipmentsListProps) {
    // Default columns if none provided
    const defaultColumns: ColumnDefinition<ShipmentItem>[] = [
        {
            key: 'tracking_number',
            header: 'Tracking Number',
            sortable: true,
        },
        {
            key: 'carrier',
            header: 'Carrier',
            sortable: true,
        },
        {
            key: 'status',
            header: 'Status',
            sortable: true,
        },
        {
            key: 'estimated_delivery',
            header: 'Est. Delivery',
            sortable: true,
        },
        {
            key: 'recipient_name',
            header: 'Recipient',
            sortable: true,
        },
        {
            key: 'package_description',
            header: 'Description',
            sortable: false,
        },
        {
            key: 'events_count',
            header: 'Events',
            sortable: true,
            align: 'center',
        },
        {
            key: 'actions',
            header: 'Actions',
            sortable: false,
            align: 'center',
        },
    ];

    const finalColumns = columns || defaultColumns;

    // Row renderer function
    const renderShipmentRow = (shipment: ShipmentItem, index: number) => (
        <>
            <TableCell>
                <div className="flex items-center gap-2">
                    <Package className="h-4 w-4 text-gray-500" />
                    <span className="font-mono text-sm">{shipment.tracking_number}</span>
                </div>
            </TableCell>
            <TableCell>
                <div className="flex items-center gap-2">
                    <Truck className="h-4 w-4 text-gray-500" />
                    <span className="capitalize">{shipment.carrier}</span>
                </div>
            </TableCell>
            <TableCell>
                <Badge variant={getStatusVariant(shipment.status)}>
                    {shipment.status}
                </Badge>
            </TableCell>
            <TableCell>
                {shipment.estimated_delivery ? (
                    <div className="flex items-center gap-2">
                        <Calendar className="h-4 w-4 text-gray-500" />
                        <span>{formatDate(shipment.estimated_delivery)}</span>
                    </div>
                ) : (
                    <span className="text-gray-400">Not specified</span>
                )}
            </TableCell>
            <TableCell>
                {shipment.recipient_name || (
                    <span className="text-gray-400">Not specified</span>
                )}
            </TableCell>
            <TableCell>
                {shipment.package_description || (
                    <span className="text-gray-400">No description</span>
                )}
            </TableCell>
            <TableCell className="text-center">
                {shipment.events_count !== undefined ? (
                    <Badge variant="outline">{shipment.events_count}</Badge>
                ) : (
                    <span className="text-gray-400">-</span>
                )}
            </TableCell>
            <TableCell>
                <div className="flex items-center gap-2">
                    {onViewDetails && (
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                                e.stopPropagation();
                                onViewDetails(shipment);
                            }}
                        >
                            View
                        </Button>
                    )}
                    {shipment.tracking_link && (
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                                e.stopPropagation();
                                window.open(shipment.tracking_link, '_blank');
                            }}
                        >
                            <ExternalLink className="h-4 w-4" />
                        </Button>
                    )}
                    {onTrackPackage && (
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                                e.stopPropagation();
                                onTrackPackage(shipment);
                            }}
                        >
                            Track
                        </Button>
                    )}
                </div>
            </TableCell>
        </>
    );

    return (
        <PaginatedDataTable
            data={shipments}
            columns={finalColumns}
            pagination={pagination}
            paginationHandlers={{
                onNextPage,
                onPrevPage,
                onFirstPage,
            }}
            onSort={onSort}
            onRowClick={onRowClick}
            rowRenderer={renderShipmentRow}
            emptyMessage={emptyMessage}
            loadingMessage={loadingMessage}
            className={className}
        />
    );
});

// Helper functions
function getStatusVariant(status: string): "default" | "secondary" | "destructive" | "outline" {
    switch (status.toLowerCase()) {
        case 'delivered':
            return 'default';
        case 'in_transit':
        case 'shipped':
            return 'secondary';
        case 'delayed':
        case 'lost':
            return 'destructive';
        default:
            return 'outline';
    }
}

function formatDate(dateString: string): string {
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString();
    } catch {
        return dateString;
    }
}

export default ShipmentsList;
