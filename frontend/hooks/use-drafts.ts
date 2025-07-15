import gatewayClient from '@/lib/gateway-client';
import { Draft, DraftStatus, DraftType } from '@/types/draft';
import { useCallback, useEffect, useState } from 'react';

interface UseDraftsOptions {
    type?: DraftType;
    status?: DraftStatus;
    search?: string;
    limit?: number;
}

interface UseDraftsReturn {
    drafts: Draft[];
    loading: boolean;
    error: string | null;
    totalCount: number;
    hasMore: boolean;
    refetch: () => Promise<void>;
    createDraft: (draft: { type: DraftType; content: string; metadata?: any }) => Promise<Draft>;
    updateDraft: (id: string, updates: Partial<Draft>) => Promise<Draft>;
    deleteDraft: (id: string) => Promise<boolean>;
}

export function useDrafts(options: UseDraftsOptions = {}): UseDraftsReturn {
    const [drafts, setDrafts] = useState<Draft[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [totalCount, setTotalCount] = useState(0);
    const [hasMore, setHasMore] = useState(false);

    const fetchDrafts = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);

            const params = new URLSearchParams();
            if (options.type) params.append('draft_type', options.type);
            if (options.status) params.append('status', options.status);
            if (options.search) params.append('search', options.search);
            if (options.limit) params.append('limit', options.limit.toString());

            const data = await gatewayClient.listDrafts({
                type: options.type,
                status: options.status,
                search: options.search,
            });

            const mappedDrafts = data.drafts.map((draft: any) => ({
                id: draft.id,
                type: draft.type as DraftType,
                status: draft.status as DraftStatus,
                content: draft.content,
                metadata: (typeof draft.metadata === 'object' && draft.metadata !== null) ? draft.metadata : {},
                isAIGenerated: draft.is_ai_generated ?? false,
                createdAt: draft.created_at,
                updatedAt: draft.updated_at,
                userId: draft.user_id,
                threadId: draft.thread_id,
            }));

            setDrafts(mappedDrafts);
            setTotalCount(data.total_count);
            setHasMore(data.has_more);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch drafts');
        } finally {
            setLoading(false);
        }
    }, [options.type, options.status, options.search, options.limit]);

    const createDraft = useCallback(async (draft: { type: DraftType; content: string; metadata?: any }): Promise<Draft> => {
        try {
            const data = await gatewayClient.createDraft({
                type: draft.type,
                content: draft.content,
                metadata: draft.metadata,
            });

            const newDraft: Draft = {
                id: data.id,
                type: data.type as DraftType,
                status: data.status as DraftStatus,
                content: data.content,
                metadata: (typeof data.metadata === 'object' && data.metadata !== null) ? data.metadata : {},
                isAIGenerated: data.is_ai_generated ?? false,
                createdAt: data.created_at,
                updatedAt: data.updated_at,
                userId: data.user_id,
                threadId: data.thread_id,
            };

            setDrafts(prev => [newDraft, ...prev]);
            return newDraft;
        } catch (err) {
            throw new Error(err instanceof Error ? err.message : 'Failed to create draft');
        }
    }, []);

    const updateDraft = useCallback(async (id: string, updates: Partial<Draft>): Promise<Draft> => {
        try {
            const data = await gatewayClient.updateDraft(id, {
                content: updates.content,
                metadata: updates.metadata as Record<string, unknown> | undefined, // Fix type error
                status: updates.status,
            });

            const updatedDraft: Draft = {
                id: data.id,
                type: data.type as DraftType,
                status: data.status as DraftStatus,
                content: data.content,
                metadata: (typeof data.metadata === 'object' && data.metadata !== null) ? data.metadata : {},
                isAIGenerated: data.is_ai_generated ?? false,
                createdAt: data.created_at,
                updatedAt: data.updated_at,
                userId: data.user_id,
                threadId: data.thread_id,
            };

            setDrafts(prev => prev.map(draft => draft.id === id ? updatedDraft : draft));
            return updatedDraft;
        } catch (err) {
            throw new Error(err instanceof Error ? err.message : 'Failed to update draft');
        }
    }, []);

    const deleteDraft = useCallback(async (id: string): Promise<boolean> => {
        try {
            await gatewayClient.deleteDraft(id);
            setDrafts(prev => prev.filter(draft => draft.id !== id));
            return true;
        } catch (err) {
            throw new Error(err instanceof Error ? err.message : 'Failed to delete draft');
        }
    }, []);

    useEffect(() => {
        fetchDrafts();
    }, [fetchDrafts]);

    return {
        drafts,
        loading,
        error,
        totalCount,
        hasMore,
        refetch: fetchDrafts,
        createDraft,
        updateDraft,
        deleteDraft,
    };
} 