import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { DraftStatus, DraftType } from '@/types/draft';
import { useState } from 'react';

export function DraftFilters({
    type,
    status,
    search,
    onChange,
}: {
    type?: DraftType;
    status?: DraftStatus;
    search?: string;
    onChange: (filters: { type?: DraftType; status?: DraftStatus; search?: string }) => void;
}) {
    const [localSearch, setLocalSearch] = useState(search || '');

    return (
        <div className="flex gap-2 mb-2">
            <Select value={type || ''} onValueChange={v => onChange({ type: v as DraftType, status, search: localSearch })}>
                <option value="">All Types</option>
                <option value="email">Email</option>
                <option value="calendar">Calendar</option>
                <option value="document">Document</option>
            </Select>
            <Select value={status || ''} onValueChange={v => onChange({ type, status: v as DraftStatus, search: localSearch })}>
                <option value="">All Status</option>
                <option value="draft">Draft</option>
                <option value="sent">Sent</option>
                <option value="archived">Archived</option>
            </Select>
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