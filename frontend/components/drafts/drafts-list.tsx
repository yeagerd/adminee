import { useDrafts } from '@/hooks/use-drafts';
import { filterDraftsBySearch, sortDraftsByUpdated } from '@/lib/draft-utils';
import { DraftStatus, DraftType } from '@/types/draft';
import { useState } from 'react';
import { DraftCard } from './draft-card';
import { DraftFilters } from './draft-filters';
import { NewDraftButton } from './new-draft-button';

export type DraftFiltersState = {
    type?: DraftType;
    status?: DraftStatus;
    search?: string;
};

export default function DraftsList() {
    const [filters, setFilters] = useState<DraftFiltersState>({ type: undefined, status: undefined, search: '' });
    const { drafts, loading, error } = useDrafts(filters);

    const sortedDrafts = sortDraftsByUpdated(filterDraftsBySearch(drafts, filters.search || ''));

    return (
        <div className="p-4">
            <div className="flex items-center justify-between mb-2">
                <h2 className="text-lg font-semibold">Drafts</h2>
                <NewDraftButton onClick={() => {/* TODO: open new draft modal */ }} />
            </div>
            <DraftFilters {...filters} onChange={setFilters} />
            {loading && <div>Loading drafts...</div>}
            {error && <div className="text-red-500">Error loading drafts.</div>}
            {!loading && sortedDrafts.length === 0 && <div>No drafts found.</div>}
            <div className="space-y-2">
                {sortedDrafts.map(draft => (
                    <DraftCard key={draft.id} draft={draft} onClick={() => {/* TODO: open draft */ }} />
                ))}
            </div>
        </div>
    );
} 