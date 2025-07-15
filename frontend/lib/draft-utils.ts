import { Draft } from '@/types/draft';

export function formatDraftDate(date: string): string {
    return new Date(date).toLocaleString();
}

export function filterDraftsBySearch(drafts: Draft[], search: string): Draft[] {
    if (!search) return drafts;
    return drafts.filter((draft: Draft) =>
        draft.content?.toLowerCase().includes(search.toLowerCase()) ||
        draft.metadata?.subject?.toLowerCase().includes(search.toLowerCase())
    );
}

export function sortDraftsByUpdated(drafts: Draft[]): Draft[] {
    return [...drafts].sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
} 