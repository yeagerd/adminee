import { Input } from '../ui/input';

export default function PackageFilters({ filters, onFiltersChange }: {
    filters: any,
    onFiltersChange: any,
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
        </div>
    );
}
