import { ExternalLink, Filter } from 'lucide-react';
import { memo, useState } from 'react';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import PaginatedDataTable, { ColumnDefinition } from '../ui/paginated-data-table';
import { TableCell } from '../ui/table';
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

interface PackageListV2Props {
    packages: Package[];
    onSort: (field: string) => void;
    editingCell: { id: string; field: string } | null;
    setEditingCell: (cell: { id: string; field: string } | null) => void;
    onCellEdit: (id: string, field: string, value: string) => void;
    onRowClick: (pkg: Package) => void;
    selectedStatusFilters: string[];
    onStatusFilterChange: (values: string[]) => void;
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
}

const PackageListV2 = memo(function PackageListV2({
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
}: PackageListV2Props) {
    const [showStatusFilter, setShowStatusFilter] = useState(false);

    // Define columns for the data table
    const columns: ColumnDefinition<Package>[] = [
        {
            key: 'tracking_number',
            header: 'Tracking Number',
            sortable: true,
        },
        {
            key: 'status',
            header: (
                <div className="flex items-center gap-1">
                    <span>Status</span>
                    <Button
                        size="sm"
                        variant="ghost"
                        className="p-1"
                        onClick={e => {
                            e.stopPropagation();
                            setShowStatusFilter(v => !v);
                        }}
                    >
                        <Filter className="h-4 w-4" />
                    </Button>
                    {showStatusFilter && (
                        <div className="absolute left-0 top-8 z-50" onClick={e => e.stopPropagation()}>
                            <MultiSelectFilter
                                options={STATUS_OPTIONS}
                                selected={selectedStatusFilters}
                                onChange={onStatusFilterChange}
                            />
                        </div>
                    )}
                </div>
            ),
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
    const renderPackageRow = (pkg: Package, index: number) => (
        <>
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
                    <span
                        className="cursor-pointer"
                        onClick={() => setEditingCell({ id: pkg.id!, field: 'tracking_number' })}
                    >
                        {pkg.tracking_number}
                    </span>
                )}
            </TableCell>
            <TableCell>
                <Badge>{pkg.status}</Badge>
            </TableCell>
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
                    <span
                        className="cursor-pointer"
                        onClick={() => setEditingCell({ id: pkg.id!, field: 'estimated_delivery' })}
                    >
                        {pkg.estimated_delivery}
                    </span>
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
                    <span
                        className="cursor-pointer"
                        onClick={() => setEditingCell({ id: pkg.id!, field: 'package_description' })}
                    >
                        {pkg.package_description}
                    </span>
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
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => window.open(pkg.tracking_link, '_blank')}
                >
                    <ExternalLink className="h-4 w-4" />
                </Button>
            </TableCell>
        </>
    );

    return (
        <PaginatedDataTable
            data={packages}
            columns={columns}
            pagination={pagination}
            paginationHandlers={{
                onNextPage,
                onPrevPage,
                onFirstPage,
            }}
            onSort={onSort}
            onRowClick={onRowClick}
            rowRenderer={renderPackageRow}
            emptyMessage="No packages found."
            loadingMessage="Loading packages..."
        />
    );
});

export default PackageListV2;
