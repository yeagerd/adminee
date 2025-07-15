import {
    DropdownMenu,
    DropdownMenuCheckboxItem,
    DropdownMenuContent,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import { DraftStatus, DraftType } from '@/types/draft';
import { useEffect, useState } from 'react';

const DRAFT_TYPES: DraftType[] = ['email', 'calendar', 'document'];
const DRAFT_STATUSES: DraftStatus[] = ['draft', 'sent', 'archived'];

export function DraftFilters({
    type,
    status,
    search,
    onChange,
    hideTypeAndStatus = false,
}: {
    type?: DraftType | DraftType[];
    status?: DraftStatus | DraftStatus[];
    search?: string;
    onChange: (filters: { type?: DraftType | DraftType[]; status?: DraftStatus | DraftStatus[]; search?: string }) => void;
    hideTypeAndStatus?: boolean;
}) {
    // Only use local search state if search input is rendered (hideTypeAndStatus)
    const [localSearch, setLocalSearch] = useState(search || '');
    const [selectedTypes, setSelectedTypes] = useState<DraftType[]>(Array.isArray(type) ? type : type ? [type] : []);
    const [selectedStatuses, setSelectedStatuses] = useState<DraftStatus[]>(Array.isArray(status) ? status : status ? [status] : []);

    // Sync localSearch with prop if hideTypeAndStatus is true
    useEffect(() => {
        if (hideTypeAndStatus) {
            setLocalSearch(search || '');
        }
    }, [search, hideTypeAndStatus]);

    if (hideTypeAndStatus) {
        return (
            <div className="flex gap-2 mb-2 w-full">
                <Input
                    placeholder="Search drafts..."
                    value={localSearch}
                    onChange={e => {
                        setLocalSearch(e.target.value);
                        onChange({ type, status, search: e.target.value });
                    }}
                    className="flex-1"
                />
            </div>
        );
    }
    return (
        <div className="flex items-center">
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <button className="relative border rounded px-3 py-2 text-sm bg-background hover:bg-accent focus:outline-none flex items-center">
                        Filters
                        {/* Show a small green dot if any filter is active */}
                        {(selectedTypes.length > 0 || selectedStatuses.length > 0) && (
                            <span className="absolute top-1 right-1 block h-2 w-2 rounded-full bg-green-500" />
                        )}
                    </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start">
                    <DropdownMenuLabel>Type</DropdownMenuLabel>
                    {DRAFT_TYPES.map((t) => (
                        <DropdownMenuCheckboxItem
                            key={t}
                            checked={selectedTypes.includes(t)}
                            onCheckedChange={(checked) => {
                                const newTypes = checked
                                    ? [...selectedTypes, t]
                                    : selectedTypes.filter((type) => type !== t);
                                setSelectedTypes(newTypes);
                                onChange({ type: newTypes, status: selectedStatuses, search });
                            }}
                        >
                            {t.charAt(0).toUpperCase() + t.slice(1)}
                        </DropdownMenuCheckboxItem>
                    ))}
                    <DropdownMenuSeparator />
                    <DropdownMenuLabel>Status</DropdownMenuLabel>
                    {DRAFT_STATUSES.map((s) => (
                        <DropdownMenuCheckboxItem
                            key={s}
                            checked={selectedStatuses.includes(s)}
                            onCheckedChange={(checked) => {
                                const newStatuses = checked
                                    ? [...selectedStatuses, s]
                                    : selectedStatuses.filter((status) => status !== s);
                                setSelectedStatuses(newStatuses);
                                onChange({ type: selectedTypes, status: newStatuses, search });
                            }}
                        >
                            {s.charAt(0).toUpperCase() + s.slice(1)}
                        </DropdownMenuCheckboxItem>
                    ))}
                </DropdownMenuContent>
            </DropdownMenu>
            {/* No search input here; search is handled in the parent */}
        </div>
    );
} 