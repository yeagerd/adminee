import { PaginationHandlers, PaginationState } from '@/components/ui/paginated-data-table';
import { useCallback, useState } from 'react';

export interface UsePaginationOptions {
    initialLimit?: number;
    onPageChange?: (cursor: string | null, direction: 'next' | 'prev' | 'first') => void;
}

export interface UsePaginationReturn {
    paginationState: PaginationState;
    paginationHandlers: PaginationHandlers;
    setPaginationData: (data: {
        hasNext: boolean;
        hasPrev: boolean;
        nextCursor?: string;
        prevCursor?: string;
        itemsCount: number;
    }) => void;
    setLoading: (loading: boolean) => void;
    resetPagination: () => void;
}

export function usePagination(options: UsePaginationOptions = {}): UsePaginationReturn {
    const { initialLimit = 20, onPageChange } = options;

    const [paginationState, setPaginationState] = useState<PaginationState>({
        hasNext: false,
        hasPrev: false,
        nextCursor: undefined,
        prevCursor: undefined,
        loading: false,
    });

    const setPaginationData = useCallback((data: {
        hasNext: boolean;
        hasPrev: boolean;
        nextCursor?: string;
        prevCursor?: string;
        itemsCount: number;
    }) => {
        setPaginationState(prev => ({
            ...prev,
            hasNext: data.hasNext,
            hasPrev: data.hasPrev,
            nextCursor: data.nextCursor,
            prevCursor: data.prevCursor,
        }));
    }, []);

    const setLoading = useCallback((loading: boolean) => {
        setPaginationState(prev => ({
            ...prev,
            loading,
        }));
    }, []);

    const resetPagination = useCallback(() => {
        setPaginationState({
            hasNext: false,
            hasPrev: false,
            nextCursor: undefined,
            prevCursor: undefined,
            loading: false,
        });
    }, []);

    const handleNextPage = useCallback(() => {
        if (!paginationState.hasNext || paginationState.loading || !paginationState.nextCursor) {
            return;
        }

        setPaginationState(prev => ({ ...prev, loading: true }));
        onPageChange?.(paginationState.nextCursor, 'next');
    }, [paginationState.hasNext, paginationState.loading, paginationState.nextCursor, onPageChange]);

    const handlePrevPage = useCallback(() => {
        if (!paginationState.hasPrev || paginationState.loading || !paginationState.prevCursor) {
            return;
        }

        setPaginationState(prev => ({ ...prev, loading: true }));
        onPageChange?.(paginationState.prevCursor, 'prev');
    }, [paginationState.hasPrev, paginationState.loading, paginationState.prevCursor, onPageChange]);

    const handleFirstPage = useCallback(() => {
        if (paginationState.loading) {
            return;
        }

        setPaginationState(prev => ({ ...prev, loading: true }));
        onPageChange?.(null, 'first');
    }, [paginationState.loading, onPageChange]);

    const paginationHandlers: PaginationHandlers = {
        onNextPage: handleNextPage,
        onPrevPage: handlePrevPage,
        onFirstPage: handleFirstPage,
    };

    return {
        paginationState,
        paginationHandlers,
        setPaginationData,
        setLoading,
        resetPagination,
    };
}
