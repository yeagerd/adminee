import { usePagination } from '@/hooks/use-pagination';
import dayjs from 'dayjs';
import isSameOrAfter from 'dayjs/plugin/isSameOrAfter';
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore';
import { AlertTriangle, Calendar, CheckCircle, Clock, ExternalLink, Plus, Truck } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ReactNode, useCallback, useEffect, useMemo, useState } from 'react';
import gatewayClient from '../../lib/gateway-client';
import { DASHBOARD_STATUS_MAPPING, PACKAGE_STATUS } from '../../lib/package-status';
import '../../styles/summary-grid.css';
import ShipmentDetailsModal from '../shipments/ShipmentDetailsModal';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Card } from '../ui/card';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../ui/dropdown-menu';
import { Input } from '../ui/input';
import PaginatedDataTable, { ColumnDefinition } from '../ui/paginated-data-table';
import { TableCell } from '../ui/table';
import type { Package } from './AddPackageModal';
import AddPackageModal from './AddPackageModal';
import LabelChip from './LabelChip';

dayjs.extend(isSameOrAfter);
dayjs.extend(isSameOrBefore);

function SummaryBox({ icon: Icon, label, value, iconClass }: { icon: ReactNode, label: string, value: number | string, iconClass: string }) {
    return (
        <Card className="container">
            <div className="flex flex-row items-center justify-center space-y-0 py-4 px-1">
                <div className="flex items-center gap-2 justify-center">
                    <div className="flex flex-col flex-wrap items-center">
                        <span className="text-2xl font-bold">{value}</span>
                        <span className="text-sm font-medium">{label}</span>
                    </div>
                    <span className={iconClass}>{Icon}</span>
                </div>
            </div>
        </Card>
    );
}

const DATE_RANGE_OPTIONS = [
    { value: '7', label: 'Last 7 days' },
    { value: '30', label: 'Last 30 days' },
    { value: '90', label: 'Last 90 days' },
    { value: 'all', label: 'All' },
];

export default function PackageDashboard() {
    const router = useRouter();
    const searchParams = useSearchParams();

    const [showAddModal, setShowAddModal] = useState(false);
    const [packages, setPackages] = useState<Package[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [sortField, setSortField] = useState('estimated_delivery');
    const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
    const [selectedPackage, setSelectedPackage] = useState<Package | null>(null);
    const [selectedStatusFilters, setSelectedStatusFilters] = useState<string[]>([]);
    const [selectedCarrierFilters, setSelectedCarrierFilters] = useState<string[]>([]);
    const [dateRange, setDateRange] = useState<'7' | '30' | '90' | 'all'>('7');

    // Performance optimizations
    const [cursorCache, setCursorCache] = useState<Map<string, unknown>>(new Map());

    // Pagination hook
    const {
        paginationState,
        paginationHandlers,
        setPaginationData,
        resetPagination,
    } = usePagination({
        initialLimit: 20,
        onPageChange: (cursor: string | null, direction: 'next' | 'prev' | 'first') => {
            if (direction === 'first') {
                loadData(null, 'next');
            } else {
                loadData(cursor, direction);
            }
        },
    });

    // Load state from URL on mount
    useEffect(() => {
        const status = searchParams.get('status');
        const carrier = searchParams.get('carrier');
        const search = searchParams.get('search');
        const dateRangeParam = searchParams.get('dateRange');

        if (status) {
            setSelectedStatusFilters([status]);
        }
        if (carrier) {
            setSelectedCarrierFilters([carrier]);
        }
        if (search) {
            setSearchTerm(search);
        }
        if (dateRangeParam && ['7', '30', '90', 'all'].includes(dateRangeParam)) {
            setDateRange(dateRangeParam as '7' | '30' | '90' | 'all');
        }
    }, [searchParams]);

    // Cursor caching functions
    const getCachedData = useCallback((cacheKey: string) => {
        return cursorCache.get(cacheKey);
    }, [cursorCache]);

    const setCachedData = useCallback((cacheKey: string, data: unknown) => {
        setCursorCache(prev => {
            const newCache = new Map(prev);
            newCache.set(cacheKey, data);
            // Limit cache size to prevent memory leaks
            if (newCache.size > 50) {
                const firstKey = newCache.keys().next().value;
                if (firstKey) {
                    newCache.delete(firstKey);
                }
            }
            return newCache;
        });
    }, []);

    // Main data loading function
    const loadData = useCallback(async (cursor: string | null = null, direction: 'next' | 'prev' = 'next') => {
        setLoading(true);
        setError(null);
        try {
            // Build filter parameters for server-side filtering
            const filterParams: {
                cursor?: string;
                limit?: number;
                direction?: 'next' | 'prev';
                status?: string;
                carrier?: string;
                tracking_number?: string;
                date_range?: string;
            } = {
                limit: 20,
                direction,
            };

            if (cursor) {
                filterParams.cursor = cursor;
            }

            // Add status filter if selected
            if (selectedStatusFilters.length > 0) {
                filterParams.status = selectedStatusFilters[0];
            }

            // Add carrier filter if selected
            if (selectedCarrierFilters.length > 0) {
                filterParams.carrier = selectedCarrierFilters[0];
            }

            // Add search filter if provided
            if (searchTerm.trim()) {
                filterParams.tracking_number = searchTerm.trim();
            }

            // Add date range filter if selected
            if (dateRange !== 'all') {
                filterParams.date_range = dateRange;
            }

            // Check cache first
            const cacheKey = JSON.stringify(filterParams);
            const cachedData = getCachedData(cacheKey);
            if (cachedData && typeof cachedData === 'object' && 'packages' in cachedData) {
                const cached = cachedData as { packages: Package[]; next_cursor?: string; prev_cursor?: string; has_next: boolean; has_prev: boolean };
                setPackages(cached.packages || []);
                setPaginationData({
                    hasNext: cached.has_next,
                    hasPrev: cached.has_prev,
                    nextCursor: cached.next_cursor,
                    prevCursor: cached.prev_cursor,
                    itemsCount: cached.packages?.length || 0,
                });
                return;
            }

            const res = await gatewayClient.getPackages(filterParams);

            // Cache the result
            setCachedData(cacheKey, res);

            setPackages(res.packages || []);
            setPaginationData({
                hasNext: res.has_next,
                hasPrev: res.has_prev,
                nextCursor: res.next_cursor,
                prevCursor: res.prev_cursor,
                itemsCount: res.packages?.length || 0,
            });

        } catch (err) {
            let errorMessage = 'Failed to fetch packages';

            if (err instanceof Error) {
                // Handle specific cursor-related errors
                if (err.message.includes('Invalid or expired cursor token')) {
                    errorMessage = 'Invalid or expired cursor token';
                    // Reset pagination state
                    resetPagination();
                } else {
                    errorMessage = err.message;
                }
            }

            setError(errorMessage);
        } finally {
            setLoading(false);
        }
    }, [selectedStatusFilters, selectedCarrierFilters, searchTerm, dateRange, getCachedData, setCachedData, setPaginationData, resetPagination]);

    // Load first page on mount and when filters change
    useEffect(() => {
        const timer = setTimeout(() => {
            loadData();
        }, 300);

        return () => clearTimeout(timer);
    }, [loadData]);

    // Update URL when filters change
    useEffect(() => {
        const newSearchParams = new URLSearchParams(searchParams.toString());

        // Update status filter
        if (selectedStatusFilters.length > 0) {
            newSearchParams.set('status', selectedStatusFilters[0]);
        } else {
            newSearchParams.delete('status');
        }

        // Update carrier filter
        if (selectedCarrierFilters.length > 0) {
            newSearchParams.set('carrier', selectedCarrierFilters[0]);
        } else {
            newSearchParams.delete('carrier');
        }

        // Update search term
        if (searchTerm.trim()) {
            newSearchParams.set('search', searchTerm.trim());
        } else {
            newSearchParams.delete('search');
        }

        // Update date range filter
        if (dateRange !== 'all') {
            newSearchParams.set('dateRange', dateRange);
        } else {
            newSearchParams.delete('dateRange');
        }

        const newURL = `${window.location.pathname}?${newSearchParams.toString()}`;
        router.push(newURL, { scroll: false });
    }, [selectedStatusFilters, selectedCarrierFilters, searchTerm, dateRange, router, searchParams]);

    const filteredAndSortedPackages = useMemo(() => {
        const filtered = [...packages];

        // Apply sorting
        return filtered.sort((a, b) => {
            let aValue: string | number | undefined = a[sortField as keyof Package] as string | number | undefined;
            let bValue: string | number | undefined = b[sortField as keyof Package] as string | number | undefined;

            // Handle date sorting
            if (sortField === 'estimated_delivery' || sortField === 'created_at' || sortField === 'updated_at') {
                aValue = dayjs(aValue as string).valueOf();
                bValue = dayjs(bValue as string).valueOf();
            }

            // Handle string sorting
            if (typeof aValue === 'string' && typeof bValue === 'string') {
                aValue = aValue.toLowerCase();
                bValue = bValue.toLowerCase();
            }

            if (sortDirection === 'asc') {
                return (aValue ?? '') < (bValue ?? '') ? -1 : (aValue ?? '') > (bValue ?? '') ? 1 : 0;
            } else {
                return (aValue ?? '') > (bValue ?? '') ? -1 : (aValue ?? '') < (bValue ?? '') ? 1 : 0;
            }
        });
    }, [packages, sortField, sortDirection]);

    const handleSort = (field: string) => {
        if (sortField === field) {
            setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortDirection('asc');
        }
    };

    const handleAddPackage = async () => {
        setShowAddModal(true);
    };

    const refreshPackages = async () => {
        await loadData();
    };



    const handleRowClick = (pkg: Package) => setSelectedPackage(pkg);

    // Define columns for the data table
    const columns: ColumnDefinition[] = [
        {
            key: 'tracking_number',
            header: 'Tracking Number',
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
            key: 'package_description',
            header: 'Description',
            sortable: false,
        },
        {
            key: 'labels',
            header: 'Labels',
            sortable: false,
        },
        {
            key: 'actions',
            header: 'Actions',
            sortable: false,
            align: 'center',
        },
    ];

    // Row renderer function
    const renderPackageRow = (pkg: Package) => (
        <>
            <TableCell>{pkg.tracking_number}</TableCell>
            <TableCell><Badge>{pkg.status}</Badge></TableCell>
            <TableCell>{pkg.estimated_delivery}</TableCell>
            <TableCell>{pkg.package_description}</TableCell>
            <TableCell>
                <div className="flex flex-wrap gap-1">
                    {(pkg.labels || []).map((label: string | { name: string }, idx: number) => (
                        <LabelChip key={idx} label={typeof label === 'string' ? label : label?.name || ''} />
                    ))}
                </div>
            </TableCell>
            <TableCell onClick={e => e.stopPropagation()}>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => { window.open(pkg.tracking_link, '_blank'); }}
                >
                    <ExternalLink className="h-4 w-4" />
                </Button>
            </TableCell>
        </>
    );

    // Calculate summary statistics
    const summaryStats = useMemo(() => {
        const total = filteredAndSortedPackages.length;
        const delivered = filteredAndSortedPackages.filter(pkg => pkg.status === PACKAGE_STATUS.DELIVERED).length;
        const inTransit = filteredAndSortedPackages.filter(pkg => pkg.status === PACKAGE_STATUS.IN_TRANSIT).length;
        const pending = filteredAndSortedPackages.filter(pkg => pkg.status === PACKAGE_STATUS.PENDING).length;
        const delayed = filteredAndSortedPackages.filter(pkg => pkg.status === PACKAGE_STATUS.DELAYED).length;

        return { total, delivered, inTransit, pending, delayed };
    }, [filteredAndSortedPackages]);

    // Get unique carriers and statuses for filters
    const availableCarriers = useMemo(() => {
        const carriers = new Set<string>();
        packages.forEach(pkg => {
            if (pkg.carrier) carriers.add(pkg.carrier);
        });
        return Array.from(carriers).sort();
    }, [packages]);

    const availableStatuses = useMemo(() => {
        const statuses = new Set<string>();
        packages.forEach(pkg => {
            if (pkg.status) statuses.add(pkg.status);
        });
        return Array.from(statuses).sort();
    }, [packages]);

    return (
        <div className="container mx-auto p-6 space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <h1 className="text-3xl font-bold">Package Dashboard</h1>
                <Button onClick={handleAddPackage} className="flex items-center gap-2">
                    <Plus className="h-4 w-4" />
                    Add Package
                </Button>
            </div>

            {/* Summary Statistics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                <SummaryBox
                    icon={<Truck className="h-6 w-6" />}
                    label="Total Packages"
                    value={summaryStats.total}
                    iconClass="text-blue-500"
                />
                <SummaryBox
                    icon={<CheckCircle className="h-6 w-6" />}
                    label="Delivered"
                    value={summaryStats.delivered}
                    iconClass="text-green-500"
                />
                <SummaryBox
                    icon={<Clock className="h-6 w-6" />}
                    label="In Transit"
                    value={summaryStats.inTransit}
                    iconClass="text-yellow-500"
                />
                <SummaryBox
                    icon={<Calendar className="h-6 w-6" />}
                    label="Pending"
                    value={summaryStats.pending}
                    iconClass="text-gray-500"
                />
                <SummaryBox
                    icon={<AlertTriangle className="h-6 w-6" />}
                    label="Delayed"
                    value={summaryStats.delayed}
                    iconClass="text-red-500"
                />
            </div>

            {/* Error Display */}
            {error && (
                <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-4">
                    <div className="flex">
                        <div className="flex-shrink-0">
                            <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                            </svg>
                        </div>
                        <div className="ml-3">
                            <h3 className="text-sm font-medium text-red-800">Error</h3>
                            <div className="mt-2 text-sm text-red-700">{error}</div>
                        </div>
                    </div>
                </div>
            )}

            {/* Filters */}
            <div className="flex flex-wrap gap-4 items-center">
                {/* Search */}
                <div className="flex-1 min-w-64">
                    <Input
                        placeholder="Search by tracking number..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full"
                    />
                </div>

                {/* Status Filter */}
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="outline">
                            Status: {selectedStatusFilters.length > 0 ? selectedStatusFilters.join(', ') : 'All'}
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent>
                        <DropdownMenuItem onClick={() => setSelectedStatusFilters([])}>
                            All Statuses
                        </DropdownMenuItem>
                        {availableStatuses.map(status => (
                            <DropdownMenuItem
                                key={status}
                                onClick={() => setSelectedStatusFilters([status])}
                            >
                                {DASHBOARD_STATUS_MAPPING[status as keyof typeof DASHBOARD_STATUS_MAPPING] || status}
                            </DropdownMenuItem>
                        ))}
                    </DropdownMenuContent>
                </DropdownMenu>

                {/* Carrier Filter */}
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="outline">
                            Carrier: {selectedCarrierFilters.length > 0 ? selectedCarrierFilters.join(', ') : 'All'}
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent>
                        <DropdownMenuItem onClick={() => setSelectedCarrierFilters([])}>
                            All Carriers
                        </DropdownMenuItem>
                        {availableCarriers.map(carrier => (
                            <DropdownMenuItem
                                key={carrier}
                                onClick={() => setSelectedCarrierFilters([carrier])}
                            >
                                {carrier}
                            </DropdownMenuItem>
                        ))}
                    </DropdownMenuContent>
                </DropdownMenu>

                {/* Date Range Filter */}
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="outline">
                            {DATE_RANGE_OPTIONS.find(opt => opt.value === dateRange)?.label || 'Date Range'}
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent>
                        {DATE_RANGE_OPTIONS.map(option => (
                            <DropdownMenuItem
                                key={option.value}
                                onClick={() => setDateRange(option.value as '7' | '30' | '90' | 'all')}
                            >
                                {option.label}
                            </DropdownMenuItem>
                        ))}
                    </DropdownMenuContent>
                </DropdownMenu>

                {/* Refresh Button */}
                <Button onClick={refreshPackages} disabled={loading}>
                    Refresh
                </Button>
            </div>

            {/* Package List */}
            <PaginatedDataTable
                data={filteredAndSortedPackages}
                columns={columns}
                pagination={paginationState}
                paginationHandlers={paginationHandlers}
                onSort={handleSort}
                onRowClick={handleRowClick}
                rowRenderer={renderPackageRow}
                emptyMessage="No packages found."
                loadingMessage="Loading packages..."
            />

            {/* Modals */}
            {showAddModal && (
                <AddPackageModal
                    onClose={() => setShowAddModal(false)}
                    onAdd={refreshPackages}
                />
            )}

            {selectedPackage && selectedPackage.id && (
                <ShipmentDetailsModal
                    isOpen={!!selectedPackage}
                    onClose={() => setSelectedPackage(null)}
                    shipment={{
                        id: selectedPackage.id,
                        tracking_number: selectedPackage.tracking_number,
                        carrier: selectedPackage.carrier,
                        status: selectedPackage.status,
                        estimated_delivery: selectedPackage.estimated_delivery,
                        actual_delivery: selectedPackage.actual_delivery,
                        recipient_name: selectedPackage.recipient_name,
                        shipper_name: selectedPackage.shipper_name,
                        package_description: selectedPackage.package_description,
                        order_number: selectedPackage.order_number,
                        tracking_link: selectedPackage.tracking_link,
                        updated_at: selectedPackage.updated_at || new Date().toISOString(),
                        events_count: selectedPackage.events?.length || 0,
                        labels: selectedPackage.labels?.map(label => typeof label === 'string' ? label : label?.name || '') || [],
                    }}
                    onShipmentUpdated={(updatedPackage) => {
                        // Update the package in the local state
                        setPackages(prevPackages =>
                            prevPackages.map(pkg =>
                                pkg.id === updatedPackage.id
                                    ? {
                                        ...pkg,
                                        tracking_number: updatedPackage.tracking_number,
                                        carrier: updatedPackage.carrier,
                                        status: updatedPackage.status,
                                        estimated_delivery: updatedPackage.estimated_delivery,
                                        actual_delivery: updatedPackage.actual_delivery,
                                        recipient_name: updatedPackage.recipient_name,
                                        shipper_name: updatedPackage.shipper_name,
                                        package_description: updatedPackage.package_description,
                                        order_number: updatedPackage.order_number,
                                        tracking_link: updatedPackage.tracking_link,
                                        updated_at: updatedPackage.updated_at,
                                        events_count: updatedPackage.events_count,
                                        labels: updatedPackage.labels,
                                    }
                                    : pkg
                            )
                        );
                    }}
                />
            )}
        </div>
    );
}
