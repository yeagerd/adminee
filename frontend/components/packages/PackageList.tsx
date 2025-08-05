import { ExternalLink, Filter } from 'lucide-react';
import { useState } from 'react';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import type { Package } from './AddPackageModal';
import LabelChip from './LabelChip';

const STATUS_OPTIONS = [
    { value: 'pending', label: 'Pending' },
    { value: 'shipped', label: 'Shipped' },
    { value: 'late', label: 'Late' },
    { value: 'delivered', label: 'Delivered' },
];

function MultiSelectFilter({ options, selected, onChange }: {
    options: { value: string, label: string }[],
    selected: string[],
    onChange: (values: string[]) => void,
}) {
    return (
        <div className="bg-white border rounded shadow p-2 min-w-[180px] z-50">
            <div className="flex gap-2 mb-2">
                <Button size="sm" variant="outline" onClick={() => onChange(options.map(o => o.value))}>All</Button>
                <Button size="sm" variant="outline" onClick={() => onChange([])}>None</Button>
            </div>
            <div className="max-h-40 overflow-y-auto">
                {options.map(opt => (
                    <label key={opt.value} className="flex items-center gap-2 cursor-pointer mb-1">
                        <input
                            type="checkbox"
                            checked={selected.includes(opt.value)}
                            onChange={e => {
                                if (e.target.checked) {
                                    onChange([...selected, opt.value]);
                                } else {
                                    onChange(selected.filter(v => v !== opt.value));
                                }
                            }}
                        />
                        {opt.label}
                    </label>
                ))}
            </div>
        </div>
    );
}

export default function PackageList({
    packages,
    onSort,
    editingCell,
    setEditingCell,
    onCellEdit,
    onRowClick,
    selectedStatusFilters,
    onStatusFilterChange,
    pagination,
    onNextPage,
    onPrevPage,
    onFirstPage,
}: {
    packages: Package[],
    onSort: (field: string) => void,
    editingCell: { id: string; field: string } | null,
    setEditingCell: (cell: { id: string; field: string } | null) => void,
    onCellEdit: (id: string, field: string, value: string) => void,
    onRowClick: (pkg: Package) => void,
    selectedStatusFilters: string[],
    onStatusFilterChange: (values: string[]) => void,
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
}) {
    const [showStatusFilter, setShowStatusFilter] = useState(false);

    return (
        <div className="overflow-x-auto">
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead className="cursor-pointer" onClick={() => onSort('tracking_number')}>Tracking Number</TableHead>
                        <TableHead className="relative">
                            <span className="cursor-pointer" onClick={() => onSort('status')}>Status</span>
                            <Button size="sm" variant="ghost" className="ml-1 p-1" onClick={e => { e.stopPropagation(); setShowStatusFilter(v => !v); }}>
                                <Filter className="h-4 w-4" />
                            </Button>
                            {showStatusFilter && (
                                <div className="absolute left-0 top-8" onClick={e => e.stopPropagation()}>
                                    <MultiSelectFilter
                                        options={STATUS_OPTIONS}
                                        selected={selectedStatusFilters}
                                        onChange={onStatusFilterChange}
                                    />
                                </div>
                            )}
                        </TableHead>
                        <TableHead className="cursor-pointer" onClick={() => onSort('estimated_delivery')}>Est. Delivery</TableHead>
                        <TableHead>Description</TableHead>
                        <TableHead>Labels</TableHead>
                        <TableHead>Actions</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {packages.length === 0 ? (
                        <TableRow>
                            <TableCell colSpan={6} className="text-center text-gray-500 py-8">No packages found.</TableCell>
                        </TableRow>
                    ) : (
                        packages.map(pkg => (
                            <TableRow key={pkg.id} className="hover:bg-blue-50 cursor-pointer" onClick={() => onRowClick(pkg)}>
                                <TableCell onClick={e => e.stopPropagation()}>
                                    {editingCell?.id === pkg.id && editingCell?.field === 'tracking_number' ? (
                                        <Input
                                            defaultValue={pkg.tracking_number}
                                            onBlur={e => onCellEdit(pkg.id!, 'tracking_number', e.target.value)}
                                            onKeyDown={e => {
                                                if (e.key === 'Enter') onCellEdit(pkg.id!, 'tracking_number', e.currentTarget.value);
                                                if (e.key === 'Escape') setEditingCell(null);
                                            }}
                                            autoFocus
                                        />
                                    ) : (
                                        <span className="cursor-pointer" onClick={() => setEditingCell({ id: pkg.id!, field: 'tracking_number' })}>{pkg.tracking_number}</span>
                                    )}
                                </TableCell>
                                <TableCell><Badge>{pkg.status}</Badge></TableCell>
                                <TableCell onClick={e => e.stopPropagation()}>
                                    {editingCell?.id === pkg.id && editingCell?.field === 'estimated_delivery' ? (
                                        <Input
                                            type="date"
                                            defaultValue={pkg.estimated_delivery}
                                            onBlur={e => onCellEdit(pkg.id!, 'estimated_delivery', e.target.value)}
                                            onKeyDown={e => {
                                                if (e.key === 'Enter') onCellEdit(pkg.id!, 'estimated_delivery', e.currentTarget.value);
                                                if (e.key === 'Escape') setEditingCell(null);
                                            }}
                                            autoFocus
                                        />
                                    ) : (
                                        <span className="cursor-pointer" onClick={() => setEditingCell({ id: pkg.id!, field: 'estimated_delivery' })}>{pkg.estimated_delivery}</span>
                                    )}
                                </TableCell>
                                <TableCell onClick={e => e.stopPropagation()}>
                                    {editingCell?.id === pkg.id && editingCell?.field === 'package_description' ? (
                                        <Input
                                            defaultValue={pkg.package_description}
                                            onBlur={e => onCellEdit(pkg.id!, 'package_description', e.target.value)}
                                            onKeyDown={e => {
                                                if (e.key === 'Enter') onCellEdit(pkg.id!, 'package_description', e.currentTarget.value);
                                                if (e.key === 'Escape') setEditingCell(null);
                                            }}
                                            autoFocus
                                        />
                                    ) : (
                                        <span className="cursor-pointer" onClick={() => setEditingCell({ id: pkg.id!, field: 'package_description' })}>{pkg.package_description}</span>
                                    )}
                                </TableCell>
                                <TableCell>
                                    <div className="flex flex-wrap gap-1">
                                        {(pkg.labels || []).map((label: string | { name: string }, idx: number) => (
                                            <LabelChip key={idx} label={typeof label === 'string' ? label : label?.name || ''} />
                                        ))}
                                    </div>
                                </TableCell>
                                <TableCell onClick={e => e.stopPropagation()}>
                                    <Button variant="ghost" size="sm" onClick={() => window.open(pkg.tracking_link, '_blank')}>
                                        <ExternalLink className="h-4 w-4" />
                                    </Button>
                                </TableCell>
                            </TableRow>
                        ))
                    )}
                </TableBody>
            </Table>
            
            {/* Pagination Controls */}
            {pagination && (
                <div className="flex items-center justify-between mt-4 px-2">
                    <div className="flex items-center gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={onFirstPage}
                            disabled={!pagination.hasPrev || pagination.loading}
                        >
                            First
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={onPrevPage}
                            disabled={!pagination.hasPrev || pagination.loading}
                        >
                            Previous
                        </Button>
                    </div>
                    
                    <div className="text-sm text-gray-600">
                        {pagination.loading ? 'Loading...' : `Showing ${packages.length} packages`}
                    </div>
                    
                    <div className="flex items-center gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={onNextPage}
                            disabled={!pagination.hasNext || pagination.loading}
                        >
                            Next
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}
