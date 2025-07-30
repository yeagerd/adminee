import dayjs from 'dayjs';
import isSameOrAfter from 'dayjs/plugin/isSameOrAfter';
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore';
import { AlertTriangle, Calendar, CheckCircle, Clock, Plus, Truck } from 'lucide-react';
import { ReactNode, useEffect, useMemo, useState } from 'react';
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
    const [showAddModal, setShowAddModal] = useState(false);
    const [packages, setPackages] = useState<Package[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [sortField, setSortField] = useState('estimated_delivery');
    const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
    const [editingCell, setEditingCell] = useState<{ id: number; field: string } | null>(null);
    const [selectedPackage, setSelectedPackage] = useState<Package | null>(null);
    const [selectedStatusFilters, setSelectedStatusFilters] = useState<string[]>([]);
    const [selectedCarrierFilters] = useState<string[]>([]);
    const [dateRange, setDateRange] = useState<'7' | '30' | '90' | 'all'>('7');

    useEffect(() => {
        setLoading(true);
        setError(null);
        gatewayClient.request('/api/v1/shipments/packages')
            .then((res) => {
                const typedRes = res as { data: Package[] };
                setPackages(typedRes.data || []);
            })
            .catch((err) => {
                setError(err.message || 'Failed to fetch packages');
            })
            .finally(() => setLoading(false));
    }, []);

    const filteredAndSortedPackages = useMemo(() => {
        const now = dayjs();
        const startDate: dayjs.Dayjs | null = dateRange !== 'all' ? now.subtract(Number(dateRange) - 1, 'day').startOf('day') : null;
        const filtered = packages.filter((pkg) => {
            const matchesSearch =
                pkg.tracking_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                pkg.recipient_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                pkg.package_description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                pkg.order_number?.toLowerCase().includes(searchTerm.toLowerCase());
            const status = pkg.status || PACKAGE_STATUS.PENDING;
            const matchesStatus = selectedStatusFilters.length === 0 || selectedStatusFilters.includes(status);
            const matchesCarrier = selectedCarrierFilters.length === 0 || selectedCarrierFilters.includes(pkg.carrier);
            // Date range filter
            if (!pkg.estimated_delivery) {
                // If no estimated_delivery, always include
                return matchesSearch && matchesStatus && matchesCarrier;
            }
            const estimatedDate = dayjs(pkg.estimated_delivery);
            let matchesDate = true;
            if (startDate && estimatedDate) {
                matchesDate = estimatedDate.isSameOrAfter(startDate, 'day') && estimatedDate.isSameOrBefore(now, 'day');
            }
            return matchesSearch && matchesStatus && matchesCarrier && matchesDate;
        });
        filtered.sort((a, b) => {
            const aValue = a[sortField] as string | number | undefined;
            const bValue = b[sortField] as string | number | undefined;
            if (typeof aValue === 'string' && typeof bValue === 'string') {
                return sortDirection === 'asc' ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
            }
            if (typeof aValue === 'number' && typeof bValue === 'number') {
                if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
                if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
                return 0;
            }
            return 0;
        });
        return filtered;
    }, [packages, searchTerm, selectedStatusFilters, selectedCarrierFilters, sortField, sortDirection, dateRange]);

    const handleSort = (field: string) => {
        if (sortField === field) {
            setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortDirection('asc');
        }
    };

    const handleCellEdit = (id: number, field: string, value: string) => {
        setPackages(packages.map((p) => (p.id === id ? { ...p, [field]: value } : p)));
        setEditingCell(null);
    };

    const handleAddPackage = async () => {
        setShowAddModal(false);
        setLoading(true);
        setError(null);
        try {
            const res = await gatewayClient.request('/api/v1/shipments/packages') as { data: Package[] };
            setPackages(res.data || []);
        } catch (err) {
            if (err instanceof Error) {
                setError(err.message);
            } else {
                setError('Failed to refresh packages');
            }
        } finally {
            setLoading(false);
        }
    };

    // Status counts for summary cards
    const statusCounts = useMemo(() => {
        const counts = { pending: 0, shipped: 0, late: 0, delivered: 0 };
        for (const p of packages) {
            const status = (p.status || PACKAGE_STATUS.PENDING) as keyof typeof DASHBOARD_STATUS_MAPPING;
            const dashboardStatus = DASHBOARD_STATUS_MAPPING[status] || 'late';
            counts[dashboardStatus as keyof typeof counts]++;
        }
        return counts;
    }, [packages]);

    // Handler for row click to show details
    const handleRowClick = (pkg: Package) => setSelectedPackage(pkg);

    return (
        <div className="max-w-6xl mx-auto py-4 space-y-3 px-4 m-1">
            {loading && <div className="text-center text-gray-500">Loading packages...</div>}
            {error && <div className="text-center text-red-500">{error}</div>}
            {/* Status Overview Cards */}
            {/* Log container size */}
            {/* Add a wrapper div for the container query context */}
            <div className="summary-container">
                <div className="summary-grid">
                    <SummaryBox
                        icon={<Clock className="h-4 w-4 flex-shrink-0" />}
                        label="Pending"
                        value={statusCounts.pending}
                        iconClass="text-yellow-600"
                    />
                    <SummaryBox
                        icon={<Truck className="h-4 w-4 flex-shrink-0" />}
                        label="Shipped"
                        value={statusCounts.shipped}
                        iconClass="text-blue-600"
                    />
                    <SummaryBox
                        icon={<AlertTriangle className="h-4 w-4 flex-shrink-0" />}
                        label="Late"
                        value={statusCounts.late}
                        iconClass="text-red-600"
                    />
                    <SummaryBox
                        icon={<CheckCircle className="h-4 w-4 flex-shrink-0" />}
                        label="Delivered"
                        value={statusCounts.delivered}
                        iconClass="text-green-600"
                    />
                </div>
            </div>
            {/* Filters and Search */}
            <div className="flex items-center gap-2 mb-3">
                <Input
                    placeholder="Search packages..."
                    className="flex-1 min-w-0 h-10"
                    value={searchTerm}
                    onChange={e => setSearchTerm(e.target.value)}
                />
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="outline" size="icon" className="h-10" aria-label="Filter by date range">
                            <Calendar className="h-5 w-5" />
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                        {DATE_RANGE_OPTIONS.map(opt => (
                            <DropdownMenuItem
                                key={opt.value}
                                onClick={() => setDateRange(opt.value as '7' | '30' | '90' | 'all')}
                                className={dateRange === opt.value ? 'font-bold bg-accent text-accent-foreground' : ''}
                            >
                                {opt.label}
                                {dateRange === opt.value && <CheckCircle className="ml-2 h-4 w-4 text-green-600" />}
                            </DropdownMenuItem>
                        ))}
                    </DropdownMenuContent>
                </DropdownMenu>
                <div className="shrink-0">
                    <Button
                        variant="default"
                        size="icon"
                        className="h-10"
                        onClick={() => setShowAddModal(true)}
                        aria-label="Add Package"
                    >
                        <Plus className="h-5 w-5" />
                    </Button>
                </div>
            </div>
            {/* Packages Table */}
            <PackageList
                packages={filteredAndSortedPackages}
                editingCell={editingCell}
                setEditingCell={setEditingCell}
                onCellEdit={handleCellEdit}
                onRowClick={handleRowClick}
                selectedStatusFilters={selectedStatusFilters}
                onStatusFilterChange={setSelectedStatusFilters}
                onSort={handleSort}
            />
            {showAddModal && (
                <AddPackageModal onClose={() => setShowAddModal(false)} onAdd={handleAddPackage} />
            )}
            {selectedPackage && (
                <PackageDetails pkg={selectedPackage} onClose={() => setSelectedPackage(null)} />
            )}
        </div>
    );
}
