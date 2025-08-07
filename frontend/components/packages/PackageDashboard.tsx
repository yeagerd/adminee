import dayjs from 'dayjs';
import isSameOrAfter from 'dayjs/plugin/isSameOrAfter';
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore';
import { AlertTriangle, Calendar, CheckCircle, Clock, Plus, Truck } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ReactNode, useCallback, useEffect, useMemo, useState } from 'react';
import gatewayClient from '../../lib/gateway-client';
import { DASHBOARD_STATUS_MAPPING, PACKAGE_STATUS } from '../../lib/package-status';
import '../../styles/summary-grid.css';
import { Button } from '../ui/button';
import { Card } from '../ui/card';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../ui/dropdown-menu';
import { Input } from '../ui/input';
import type { Package } from './AddPackageModal';
import AddPackageModal from './AddPackageModal';
import PackageDetails from './PackageDetails';
import PackageList from './PackageList';

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
    const [editingCell, setEditingCell] = useState<{ id: string; field: string } | null>(null);
    const [selectedPackage, setSelectedPackage] = useState<Package | null>(null);
    const [selectedStatusFilters, setSelectedStatusFilters] = useState<string[]>([]);
    const [selectedCarrierFilters, setSelectedCarrierFilters] = useState<string[]>([]);
    const [dateRange, setDateRange] = useState<'7' | '30' | '90' | 'all'>('7');

    // Cursor-based pagination state
    const [, setCurrentCursor] = useState<string | null>(null);
    const [nextCursor, setNextCursor] = useState<string | null>(null);
    const [prevCursor, setPrevCursor] = useState<string | null>(null);
    const [hasNext, setHasNext] = useState(false);
    const [hasPrev, setHasPrev] = useState(false);
    const [paginationLoading, setPaginationLoading] = useState(false);

    // Performance optimizations
    const [cursorCache, setCursorCache] = useState<Map<string, unknown>>(new Map());

    // Load state from URL on mount
    useEffect(() => {
        const cursor = searchParams.get('cursor');
        const status = searchParams.get('status');
        const carrier = searchParams.get('carrier');
        const search = searchParams.get('search');
        const dateRangeParam = searchParams.get('dateRange');

        if (cursor) {
            setCurrentCursor(cursor);
        }
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
                limit: number;
                direction: 'next' | 'prev';
                cursor?: string;
                status?: string;
                carrier?: string;
                tracking_number?: string;
                date_range?: string;
            } = {
                limit: 20,
                direction
            };

            // Use cursor from parameter or from URL
            const cursorToUse = cursor || searchParams.get('cursor');
            if (cursorToUse) {
                filterParams.cursor = cursorToUse;
            }

            // Add status filters if selected
            if (selectedStatusFilters.length > 0) {
                filterParams.status = selectedStatusFilters[0];
            }

            // Add carrier filters if selected
            if (selectedCarrierFilters.length > 0) {
                filterParams.carrier = selectedCarrierFilters[0];
            }

            // Add search term if provided
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
                setNextCursor(cached.next_cursor || null);
                setPrevCursor(cached.prev_cursor || null);
                setHasNext(cached.has_next);
                setHasPrev(cached.has_prev);
                setCurrentCursor(cursorToUse);
                return;
            }

            const res = await gatewayClient.getPackages(filterParams);

            // Cache the result
            setCachedData(cacheKey, res);

            setPackages(res.packages || []);
            setNextCursor(res.next_cursor || null);
            setPrevCursor(res.prev_cursor || null);
            setHasNext(res.has_next);
            setHasPrev(res.has_prev);
            setCurrentCursor(cursorToUse);

        } catch (err) {
            let errorMessage = 'Failed to fetch packages';

            if (err instanceof Error) {
                // Handle specific cursor-related errors
                if (err.message.includes('Invalid or expired cursor token')) {
                    errorMessage = 'Invalid or expired cursor token';
                    // Reset pagination state
                    setNextCursor(null);
                    setPrevCursor(null);
                    setHasNext(false);
                    setHasPrev(false);
                    setCurrentCursor(null);
                } else {
                    errorMessage = err.message;
                }
            }

            setError(errorMessage);
        } finally {
            setLoading(false);
        }
    }, [selectedStatusFilters, selectedCarrierFilters, searchTerm, dateRange, getCachedData, setCachedData, searchParams]);

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

        // Update cursor
        newSearchParams.delete('cursor');

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
    }, [selectedStatusFilters, selectedCarrierFilters, searchTerm, dateRange, searchParams, router]);

    const filteredAndSortedPackages = useMemo(() => {
        let filtered = [...packages];

        // Apply sorting
        filtered.sort((a, b) => {
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

        return filtered;
    }, [packages, sortField, sortDirection]);

    const handleSort = (field: string) => {
        if (sortField === field) {
            setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortDirection('asc');
        }
    };

    const handleCellEdit = (id: string, field: string, value: string) => {
        // Implementation for cell editing
        console.log('Cell edit:', { id, field, value });
    };

    const handleAddPackage = async () => {
        setShowAddModal(true);
    };

    const refreshPackages = async () => {
        await loadData();
    };

    const loadNextPage = async () => {
        if (!hasNext || !nextCursor || paginationLoading) return;

        setPaginationLoading(true);
        try {
            await loadData(nextCursor, 'next');

            // Update URL with cursor
            const newSearchParams = new URLSearchParams(searchParams.toString());
            newSearchParams.set('cursor', nextCursor);
            const newURL = `${window.location.pathname}?${newSearchParams.toString()}`;
            router.push(newURL, { scroll: false });
        } finally {
            setPaginationLoading(false);
        }
    };

    const loadPrevPage = async () => {
        if (!hasPrev || !prevCursor || paginationLoading) return;

        setPaginationLoading(true);
        try {
            await loadData(prevCursor, 'prev');

            // Update URL with cursor
            const newSearchParams = new URLSearchParams(searchParams.toString());
            newSearchParams.set('cursor', prevCursor);
            const newURL = `${window.location.pathname}?${newSearchParams.toString()}`;
            router.push(newURL, { scroll: false });
        } finally {
            setPaginationLoading(false);
        }
    };

    const handleRowClick = (pkg: Package) => setSelectedPackage(pkg);

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
            <PackageList
                packages={filteredAndSortedPackages}
                onSort={handleSort}
                onCellEdit={handleCellEdit}
                onRowClick={handleRowClick}
                editingCell={editingCell}
                setEditingCell={setEditingCell}
                selectedStatusFilters={selectedStatusFilters}
                onStatusFilterChange={setSelectedStatusFilters}
                pagination={{
                    hasNext,
                    hasPrev,
                    nextCursor: nextCursor || undefined,
                    prevCursor: prevCursor || undefined,
                    loading: paginationLoading
                }}
                onNextPage={loadNextPage}
                onPrevPage={loadPrevPage}
                onFirstPage={() => loadData()}
            />

            {/* Modals */}
            {showAddModal && (
                <AddPackageModal
                    onClose={() => setShowAddModal(false)}
                    onAdd={refreshPackages}
                />
            )}

            {selectedPackage && (
                <PackageDetails
                    pkg={selectedPackage}
                    onClose={() => setSelectedPackage(null)}
                    onRefresh={refreshPackages}
                />
            )}
        </div>
    );
}
