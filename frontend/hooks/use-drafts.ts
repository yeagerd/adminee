import { Draft, DraftStatus, DraftType } from '@/types/draft';
import { useCallback } from 'react';
import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then(res => res.json());

function mapDraftFromApi(apiDraft: any): Draft {
    return {
        id: apiDraft.id,
        type: apiDraft.type,
        status: apiDraft.status,
        content: apiDraft.content,
        metadata: apiDraft.metadata,
        isAIGenerated: apiDraft.is_ai_generated ?? false,
        createdAt: apiDraft.created_at,
        updatedAt: apiDraft.updated_at,
        userId: apiDraft.user_id,
        threadId: apiDraft.thread_id,
    };
}

export function useDrafts({ type, status, search }: { type?: DraftType | DraftType[]; status?: DraftStatus | DraftStatus[]; search?: string }) {
    const params = new URLSearchParams();
    if (Array.isArray(type)) {
        type.forEach(t => params.append('draft_type', t));
    } else if (type) {
        params.append('draft_type', type);
    }
    if (Array.isArray(status)) {
        status.forEach(s => params.append('status', s));
    } else if (status) {
        params.append('status', status);
    }
    if (search) params.append('search', search);
    const url = `/api/user-drafts?${params.toString()}`;

    const { data, error, isLoading, mutate } = useSWR(url, fetcher);

    const drafts: Draft[] = data?.drafts ? data.drafts.map(mapDraftFromApi) : [];
    const refetch = useCallback(() => mutate(), [mutate]);

    return {
        drafts,
        isLoading,
        error,
        refetch,
        totalCount: data?.total_count || 0,
        hasMore: data?.has_more || false,
    };
} 