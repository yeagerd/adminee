import { Input } from '@/components/ui/input';
import { useDrafts } from '@/hooks/use-drafts';
import { filterDraftsBySearch, sortDraftsByUpdated } from '@/lib/draft-utils';
import { DraftStatus, DraftType } from '@/types/draft';
import { useState } from 'react';
import { DraftCard } from './draft-card';
import { DraftFilters } from './draft-filters';
import { NewDraftButton } from './new-draft-button';

export type DraftFiltersState = {
    type?: DraftType | DraftType[];
    status?: DraftStatus | DraftStatus[];
    search?: string;
};

export default function DraftsList() {
    const [filters, setFilters] = useState<DraftFiltersState>({ type: [], status: [], search: '' });
    const { drafts, isLoading, error } = useDrafts(filters);

    const sortedDrafts = sortDraftsByUpdated(filterDraftsBySearch(drafts, filters.search || ''));

    return (
        <div className="p-4">
            <div className="flex items-center gap-2 mb-2 w-full">
                <Input
                    placeholder="Search drafts..."
                    value={filters.search || ''}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFilters(f => ({ ...f, search: e.target.value }))}
                    className="flex-1 min-w-0"
                />
                <div className="shrink-0">
                    <DraftFilters
                        type={filters.type}
                        status={filters.status}
                        onChange={f => setFilters(prev => ({ ...prev, ...f }))}
                    />
                </div>
                <div className="shrink-0">
                    <NewDraftButton onClick={() => {/* TODO: open new draft modal */ }} />
                </div>
            </div>
            {/* Show type/status filters below if needed */}
            {/* <DraftFilters {...filters} onChange={setFilters} /> */}
            {isLoading && <div>Loading drafts...</div>}
            {error && <div className="text-red-500">Error loading drafts.</div>}
            {!isLoading && !error && sortedDrafts.length === 0 && <div>No drafts found.</div>}
            <div className="space-y-2">
                {sortedDrafts.map(draft => (
                    <DraftCard key={draft.id} draft={draft} onClick={() => {/* TODO: open draft */ }} />
                ))}
            </div>
        </div>
    );
} 