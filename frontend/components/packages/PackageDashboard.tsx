import dayjs from 'dayjs';
import isSameOrAfter from 'dayjs/plugin/isSameOrAfter';
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore';
import { AlertTriangle, Calendar, CheckCircle, Clock, Plus, Truck } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import gatewayClient from '../../lib/gateway-client';
import { Button } from '../ui/button';
import { Card, CardHeader } from '../ui/card';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../ui/dropdown-menu';
import { Input } from '../ui/input';
import AddPackageModal from './AddPackageModal';
import PackageDetails from './PackageDetails';
import PackageList from './PackageList';

dayjs.extend(isSameOrAfter);
dayjs.extend(isSameOrBefore);

const STATUS_OPTIONS = [
    { value: 'all', label: 'All Status' },
    { value: 'pending', label: 'Pending' },
    { value: 'shipped', label: 'Shipped' },
    { value: 'late', label: 'Late' },
    { value: 'delivered', label: 'Delivered' },
];

const CARRIER_OPTIONS = [
    { value: 'all', label: 'All Carriers' },
    { value: 'UPS', label: 'UPS' },
    { value: 'FedEx', label: 'FedEx' },
    { value: 'USPS', label: 'USPS' },
    { value: 'DHL', label: 'DHL' },
    { value: 'Amazon', label: 'Amazon' },
];

const DATE_RANGE_OPTIONS = [
    { value: '7', label: 'Last 7 days' },
    { value: '30', label: 'Last 30 days' },
    { value: '90', label: 'Last 90 days' },
    { value: 'all', label: 'All' },
];

export default function PackageDashboard() {
    const [showAddModal, setShowAddModal] = useState(false);
    const [packages, setPackages] = useState<any[]>([]); // TODO: Replace any with proper type
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');
    const [carrierFilter, setCarrierFilter] = useState('all');
    const [sortField, setSortField] = useState('estimated_delivery');
    const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
    const [editingCell, setEditingCell] = useState<{ id: number; field: string } | null>(null);
    const [selectedPackage, setSelectedPackage] = useState<any | null>(null);
    const [selectedStatusFilters, setSelectedStatusFilters] = useState<string[]>([]);
    const [selectedCarrierFilters, setSelectedCarrierFilters] = useState<string[]>([]);
    const [dateRange, setDateRange] = useState<'7' | '30' | '90' | 'all'>('7');

    useEffect(() => {
        setLoading(true);
        setError(null);
        gatewayClient.request('/api/packages')
            .then((res: any) => {
                // If backend returns { data: [...], pagination: {...} }
                setPackages(res.data || []);
            })
            .catch((err) => {
                setError(err.message || 'Failed to fetch packages');
            })
            .finally(() => setLoading(false));
    }, []);

    const filteredAndSortedPackages = useMemo(() => {
        const now = dayjs();
        let startDate: dayjs.Dayjs | null = null;
        if (dateRange !== 'all') {
            startDate = now.subtract(Number(dateRange) - 1, 'day').startOf('day');
        }
        const filtered = packages.filter((pkg) => {
            const matchesSearch =
                pkg.tracking_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                pkg.recipient_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                pkg.package_description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                pkg.order_number?.toLowerCase().includes(searchTerm.toLowerCase());
            const status = pkg.status || 'pending';
            const matchesStatus = selectedStatusFilters.length === 0 || selectedStatusFilters.includes(status);
            const matchesCarrier = selectedCarrierFilters.length === 0 || selectedCarrierFilters.includes(pkg.carrier);
            // Date range filter
            if (!pkg.shipped_at) {
                // If no shipped_at, always include
                return matchesSearch && matchesStatus && matchesCarrier;
            }
            let shippedDate = dayjs(pkg.shipped_at);
            let matchesDate = true;
            if (startDate && shippedDate) {
                matchesDate = shippedDate.isSameOrAfter(startDate, 'day') && shippedDate.isSameOrBefore(now, 'day');
            }
            return matchesSearch && matchesStatus && matchesCarrier && matchesDate;
        });
        filtered.sort((a, b) => {
            let aValue = a[sortField];
            let bValue = b[sortField];
            if (typeof aValue === 'string' && typeof bValue === 'string') {
                return sortDirection === 'asc' ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
            }
            if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
            if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
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
        setPackages(packages.map((pkg) => (pkg.id === id ? { ...pkg, [field]: value } : pkg)));
        setEditingCell(null);
    };

    const handleAddPackage = async (pkg: any) => {
        setShowAddModal(false);
        setLoading(true);
        setError(null);
        try {
            const res: any = await gatewayClient.request('/api/packages');
            setPackages(res.data || []);
        } catch (err: any) {
            setError(err.message || 'Failed to refresh packages');
        } finally {
            setLoading(false);
        }
    };

    // Status counts for summary cards
    const statusCounts = useMemo(() => {
        const counts = { pending: 0, shipped: 0, late: 0, delivered: 0 };
        packages.forEach((pkg) => {
            const status = (pkg.status || 'pending') as keyof typeof counts;
            if (counts[status] !== undefined) counts[status]++;
        });
        return counts;
    }, [packages]);

    // Handler for row click to show details
    const handleRowClick = (pkg: any) => setSelectedPackage(pkg);

    return (
        <div className="max-w-6xl mx-auto py-4 space-y-3 px-4 m-1">
            {loading && <div className="text-center text-gray-500">Loading packages...</div>}
            {error && <div className="text-center text-red-500">{error}</div>}
            {/* Status Overview Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-center space-y-0 py-4 px-2">
                        <div className="flex items-center gap-2 w-full justify-center">
                            <span className="text-2xl font-bold">{statusCounts.pending}</span>
                            <span className="text-sm font-medium hidden md:inline">Pending</span>
                            <Clock className="h-4 w-4 text-yellow-600 flex-shrink-0" />
                        </div>
                    </CardHeader>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-center space-y-0 py-4 px-2">
                        <div className="flex items-center gap-2 w-full justify-center">
                            <span className="text-2xl font-bold">{statusCounts.shipped}</span>
                            <span className="text-sm font-medium hidden md:inline">Shipped</span>
                            <Truck className="h-4 w-4 text-blue-600 flex-shrink-0" />
                        </div>
                    </CardHeader>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-center space-y-0 py-4 px-2">
                        <div className="flex items-center gap-2 w-full justify-center">
                            <span className="text-2xl font-bold">{statusCounts.late}</span>
                            <span className="text-sm font-medium hidden md:inline">Late</span>
                            <AlertTriangle className="h-4 w-4 text-red-600 flex-shrink-0" />
                        </div>
                    </CardHeader>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-center space-y-0 py-4 px-2">
                        <div className="flex items-center gap-2 w-full justify-center">
                            <span className="text-2xl font-bold">{statusCounts.delivered}</span>
                            <span className="text-sm font-medium hidden md:inline">Delivered</span>
                            <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0" />
                        </div>
                    </CardHeader>
                </Card>
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
                onSort={handleSort}
                sortField={sortField}
                sortDirection={sortDirection}
                editingCell={editingCell}
                setEditingCell={setEditingCell}
                onCellEdit={handleCellEdit}
                onRowClick={handleRowClick}
                selectedStatusFilters={selectedStatusFilters}
                selectedCarrierFilters={selectedCarrierFilters}
                onStatusFilterChange={setSelectedStatusFilters}
                onCarrierFilterChange={setSelectedCarrierFilters}
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
