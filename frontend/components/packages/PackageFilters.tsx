import { Input } from '../ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';

export default function PackageFilters({ filters, onFiltersChange, statusOptions, carrierOptions }: {
    filters: any,
    onFiltersChange: any,
    statusOptions: { value: string, label: string }[],
    carrierOptions: { value: string, label: string }[],
}) {
    return (
        <div className="flex flex-col sm:flex-row gap-4 mb-4">
            <div className="relative flex-1">
                <Input
                    className="pl-10"
                    placeholder="Search packages..."
                    value={filters.searchTerm}
                    onChange={e => onFiltersChange({ ...filters, searchTerm: e.target.value })}
                />
            </div>
            <Select value={filters.statusFilter} onValueChange={v => onFiltersChange({ ...filters, statusFilter: v })}>
                <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="Filter by status" />
                </SelectTrigger>
                <SelectContent>
                    {statusOptions.map(opt => (
                        <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                    ))}
                </SelectContent>
            </Select>
            <Select value={filters.carrierFilter} onValueChange={v => onFiltersChange({ ...filters, carrierFilter: v })}>
                <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="Filter by carrier" />
                </SelectTrigger>
                <SelectContent>
                    {carrierOptions.map(opt => (
                        <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                    ))}
                </SelectContent>
            </Select>
        </div>
    );
}
