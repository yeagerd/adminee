import { ExternalLink } from 'lucide-react';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import LabelChip from './LabelChip';

export default function PackageList({
    packages,
    onSort,
    sortField,
    sortDirection,
    editingCell,
    setEditingCell,
    onCellEdit,
    onRowClick,
}: {
    packages: any[],
    onSort: (field: string) => void,
    sortField: string,
    sortDirection: 'asc' | 'desc',
    editingCell: { id: number; field: string } | null,
    setEditingCell: (cell: { id: number; field: string } | null) => void,
    onCellEdit: (id: number, field: string, value: string) => void,
    onRowClick: (pkg: any) => void,
}) {
    return (
        <div className="overflow-x-auto">
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead className="cursor-pointer" onClick={() => onSort('tracking_number')}>Tracking Number</TableHead>
                        <TableHead className="cursor-pointer" onClick={() => onSort('carrier')}>Carrier</TableHead>
                        <TableHead className="cursor-pointer" onClick={() => onSort('status')}>Status</TableHead>
                        <TableHead className="cursor-pointer" onClick={() => onSort('estimated_delivery')}>Est. Delivery</TableHead>
                        <TableHead className="cursor-pointer" onClick={() => onSort('recipient_name')}>Recipient</TableHead>
                        <TableHead>Description</TableHead>
                        <TableHead>Labels</TableHead>
                        <TableHead>Actions</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {packages.length === 0 ? (
                        <TableRow>
                            <TableCell colSpan={8} className="text-center text-gray-500 py-8">No packages found.</TableCell>
                        </TableRow>
                    ) : (
                        packages.map(pkg => (
                            <TableRow key={pkg.id} className="hover:bg-blue-50 cursor-pointer" onClick={() => onRowClick(pkg)}>
                                <TableCell onClick={e => e.stopPropagation()}>
                                    {editingCell?.id === pkg.id && editingCell?.field === 'tracking_number' ? (
                                        <Input
                                            defaultValue={pkg.tracking_number}
                                            onBlur={e => onCellEdit(pkg.id, 'tracking_number', e.target.value)}
                                            onKeyDown={e => { if (e.key === 'Enter') onCellEdit(pkg.id, 'tracking_number', e.currentTarget.value); }}
                                            autoFocus
                                        />
                                    ) : (
                                        <span className="cursor-pointer" onClick={() => setEditingCell({ id: pkg.id, field: 'tracking_number' })}>{pkg.tracking_number}</span>
                                    )}
                                </TableCell>
                                <TableCell><Badge variant="outline">{pkg.carrier}</Badge></TableCell>
                                <TableCell><Badge>{pkg.status}</Badge></TableCell>
                                <TableCell onClick={e => e.stopPropagation()}>
                                    {editingCell?.id === pkg.id && editingCell?.field === 'estimated_delivery' ? (
                                        <Input
                                            type="date"
                                            defaultValue={pkg.estimated_delivery}
                                            onBlur={e => onCellEdit(pkg.id, 'estimated_delivery', e.target.value)}
                                            onKeyDown={e => { if (e.key === 'Enter') onCellEdit(pkg.id, 'estimated_delivery', e.currentTarget.value); }}
                                            autoFocus
                                        />
                                    ) : (
                                        <span className="cursor-pointer" onClick={() => setEditingCell({ id: pkg.id, field: 'estimated_delivery' })}>{pkg.estimated_delivery}</span>
                                    )}
                                </TableCell>
                                <TableCell onClick={e => e.stopPropagation()}>
                                    {editingCell?.id === pkg.id && editingCell?.field === 'recipient_name' ? (
                                        <Input
                                            defaultValue={pkg.recipient_name}
                                            onBlur={e => onCellEdit(pkg.id, 'recipient_name', e.target.value)}
                                            onKeyDown={e => { if (e.key === 'Enter') onCellEdit(pkg.id, 'recipient_name', e.currentTarget.value); }}
                                            autoFocus
                                        />
                                    ) : (
                                        <span className="cursor-pointer" onClick={() => setEditingCell({ id: pkg.id, field: 'recipient_name' })}>{pkg.recipient_name}</span>
                                    )}
                                </TableCell>
                                <TableCell onClick={e => e.stopPropagation()}>
                                    {editingCell?.id === pkg.id && editingCell?.field === 'package_description' ? (
                                        <Input
                                            defaultValue={pkg.package_description}
                                            onBlur={e => onCellEdit(pkg.id, 'package_description', e.target.value)}
                                            onKeyDown={e => { if (e.key === 'Enter') onCellEdit(pkg.id, 'package_description', e.currentTarget.value); }}
                                            autoFocus
                                        />
                                    ) : (
                                        <span className="cursor-pointer" onClick={() => setEditingCell({ id: pkg.id, field: 'package_description' })}>{pkg.package_description}</span>
                                    )}
                                </TableCell>
                                <TableCell>
                                    <div className="flex flex-wrap gap-1">
                                        {(pkg.labels || []).map((label: string, idx: number) => (
                                            <LabelChip key={idx} label={label} />
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
        </div>
    );
}
