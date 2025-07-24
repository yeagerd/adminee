import { AlertTriangle, CheckCircle, Clock, Plus, Truck } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import gatewayClient from '../../lib/gateway-client';
import { Button } from '../ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import AddPackageModal from './AddPackageModal';
import PackageDetails from './PackageDetails';
import PackageFilters from './PackageFilters';
import PackageList from './PackageList';

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
        const filtered = packages.filter((pkg) => {
            const matchesSearch =
                pkg.tracking_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                pkg.recipient_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                pkg.package_description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                pkg.order_number?.toLowerCase().includes(searchTerm.toLowerCase());
            const status = pkg.status || 'pending';
            const matchesStatus = statusFilter === 'all' || status === statusFilter;
            const matchesCarrier = carrierFilter === 'all' || pkg.carrier === carrierFilter;
            return matchesSearch && matchesStatus && matchesCarrier;
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
    }, [packages, searchTerm, statusFilter, carrierFilter, sortField, sortDirection]);

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

    const handleAddPackage = (pkg: any) => {
        setPackages((prev) => [pkg, ...prev]);
        setShowAddModal(false);
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
        <div className="max-w-6xl mx-auto py-8 space-y-6">
            {loading && <div className="text-center text-gray-500">Loading packages...</div>}
            {error && <div className="text-center text-red-500">{error}</div>}
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-3xl font-bold">Package Tracker</h1>
                    <p className="text-muted-foreground">Track shipments across all your projects</p>
                </div>
                <Button onClick={() => setShowAddModal(true)}>
                    <Plus className="h-4 w-4 mr-2" /> Add Package
                </Button>
            </div>
            {/* Status Overview Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Pending</CardTitle>
                        <Clock className="h-4 w-4 text-yellow-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{statusCounts.pending}</div>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Shipped</CardTitle>
                        <Truck className="h-4 w-4 text-blue-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{statusCounts.shipped}</div>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Late</CardTitle>
                        <AlertTriangle className="h-4 w-4 text-red-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{statusCounts.late}</div>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Delivered</CardTitle>
                        <CheckCircle className="h-4 w-4 text-green-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{statusCounts.delivered}</div>
                    </CardContent>
                </Card>
            </div>
            {/* Filters and Search */}
            <PackageFilters
                filters={{ searchTerm, statusFilter, carrierFilter }}
                onFiltersChange={({ searchTerm, statusFilter, carrierFilter }: any) => {
                    setSearchTerm(searchTerm);
                    setStatusFilter(statusFilter);
                    setCarrierFilter(carrierFilter);
                }}
                statusOptions={STATUS_OPTIONS}
                carrierOptions={CARRIER_OPTIONS}
            />
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
