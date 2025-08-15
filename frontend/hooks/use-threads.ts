import { officeApi } from '@/api';
import { EmailThread } from '@/types/office-service';
import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';

interface UseThreadsOptions {
    providers?: string[];
    limit?: number;
    includeBody?: boolean;
    labels?: string[];
    folderId?: string;
    q?: string;
    autoFetch?: boolean;
}

interface UseThreadsReturn {
    threads: EmailThread[];
    selectedThread: EmailThread | null;
    selectedMessageId: string | null;
    loading: boolean;
    error: string | null;
    hasMore: boolean;
    fetchThreads: (options?: Partial<UseThreadsOptions>) => Promise<void>;
    fetchThread: (threadId: string) => Promise<void>;
    fetchMessageThread: (messageId: string) => Promise<void>;
    selectThread: (threadId: string) => void;
    selectMessage: (messageId: string) => void;
    clearSelection: () => void;
    refreshThreads: () => Promise<void>;
}

export const useThreads = (initialOptions: UseThreadsOptions = {}): UseThreadsReturn => {
    const [threads, setThreads] = useState<EmailThread[]>([]);
    const [selectedThread, setSelectedThread] = useState<EmailThread | null>(null);
    const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [hasMore, setHasMore] = useState(false);
    const [options] = useState<UseThreadsOptions>({
        providers: ['google', 'microsoft'],
        limit: 50,
        includeBody: false,
        autoFetch: true,
        ...initialOptions,
    });

    const fetchThreads = useCallback(async (fetchOptions?: Partial<UseThreadsOptions>) => {
        const mergedOptions = { ...options, ...fetchOptions };
        setLoading(true);
        setError(null);

        try {
            const response = await officeApi.getThreads(
                mergedOptions.providers,
                mergedOptions.limit,
                mergedOptions.includeBody,
                mergedOptions.labels,
                mergedOptions.folderId,
                mergedOptions.q
            );

            if (response.success && response.data) {
                setThreads(response.data.threads || []);
                setHasMore(response.data.has_more || false);
            } else {
                throw new Error('Failed to fetch threads');
            }
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to fetch threads';
            setError(errorMessage);
            toast.error(errorMessage);
        } finally {
            setLoading(false);
        }
    }, [options]);

    const fetchThread = useCallback(async (threadId: string) => {
        setLoading(true);
        setError(null);

        try {
            const response = await officeApi.getThread(threadId, true);

            if (response.success && response.data) {
                setSelectedThread(response.data.thread);
            } else {
                throw new Error('Failed to fetch thread');
            }
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to fetch thread';
            setError(errorMessage);
            toast.error(errorMessage);
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchMessageThread = useCallback(async (messageId: string) => {
        setLoading(true);
        setError(null);

        try {
            const response = await officeApi.getMessageThread(messageId, true);

            if (response.success && response.data) {
                setSelectedThread(response.data.thread);
            } else {
                throw new Error('Failed to fetch message thread');
            }
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to fetch message thread';
            setError(errorMessage);
            toast.error(errorMessage);
        } finally {
            setLoading(false);
        }
    }, []);

    const selectThread = useCallback((threadId: string) => {
        const thread = threads.find(t => t.id === threadId);
        if (thread) {
            setSelectedThread(thread);
            setSelectedMessageId(null);
        }
    }, [threads]);

    const selectMessage = useCallback((messageId: string) => {
        setSelectedMessageId(messageId);
    }, []);

    const clearSelection = useCallback(() => {
        setSelectedThread(null);
        setSelectedMessageId(null);
    }, []);

    const refreshThreads = useCallback(async () => {
        await fetchThreads();
    }, [fetchThreads]);

    // Auto-fetch threads on mount and when options change
    useEffect(() => {
        if (options.autoFetch) {
            fetchThreads();
        }
    }, [options.autoFetch, fetchThreads]);

    return {
        threads,
        selectedThread,
        selectedMessageId,
        loading,
        error,
        hasMore,
        fetchThreads,
        fetchThread,
        fetchMessageThread,
        selectThread,
        selectMessage,
        clearSelection,
        refreshThreads,
    };
}; 