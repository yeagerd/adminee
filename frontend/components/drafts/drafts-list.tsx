import { Input } from '@/components/ui/input';
import { useDrafts } from '@/hooks/use-drafts';
import { filterDraftsBySearch, sortDraftsByUpdated } from '@/lib/draft-utils';
import { DraftStatus, DraftType } from '@/types/draft';
import { useState } from 'react';
import { DraftCard } from './draft-card';
import { DraftFilters } from './draft-filters';
import { NewDraftButton } from './new-draft-button';

export type DraftFiltersState = {
    type: DraftType[];
    status: DraftStatus[];
    search: string;
};

export default function DraftsList() {
    const [filters, setFilters] = useState<DraftFiltersState>({ type: [], status: [], search: '' });
    // Convert arrays to undefined, single value, or array for useDrafts
    const useDraftsFilters = {
        type: filters.type.length === 0 ? undefined : filters.type.length === 1 ? filters.type[0] : filters.type,
        status: filters.status.length === 0 ? undefined : filters.status.length === 1 ? filters.status[0] : filters.status,
        search: filters.search,
    };
    const { drafts, loading, error } = useDrafts(useDraftsFilters);

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
                        onChange={f => setFilters(prev => ({
                            ...prev,
                            ...f,
                            // Ensure search is always a string, never undefined
                            search: f.search ?? prev.search,
                            type: f.type ? (Array.isArray(f.type) ? f.type : [f.type]) : [],
                            status: f.status ? (Array.isArray(f.status) ? f.status : [f.status]) : [],
                        }))}
                    />
                </div>
                <div className="shrink-0">
                    <NewDraftButton onClick={() => {/* TODO: open new draft modal */ }} />
                </div>
            </div>
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