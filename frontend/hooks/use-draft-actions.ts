import { DraftActionResult, draftService } from '@/services/draft-service';
import { Draft } from '@/types/draft';
import { useCallback, useState } from 'react';

export interface UseDraftActionsReturn {
    isExecuting: boolean;
    error: string | null;
    executeAction: (action: 'send' | 'save' | 'discard', draft: Draft) => Promise<DraftActionResult>;
    clearError: () => void;
}

export function useDraftActions(): UseDraftActionsReturn {
    const [isExecuting, setIsExecuting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const executeAction = useCallback(async (action: 'send' | 'save' | 'discard', draft: Draft): Promise<DraftActionResult> => {
        setIsExecuting(true);
        setError(null);

        try {
            let result: DraftActionResult;

            switch (action) {
                case 'send':
                    result = await draftService.sendDraft(draft);
                    break;
                case 'save':
                    result = await draftService.saveDraft(draft);
                    break;
                case 'discard':
                    const success = await draftService.discardDraft(draft.id);
                    result = { success, draftId: draft.id };
                    break;
                default:
                    throw new Error(`Unknown action: ${action}`);
            }

            if (!result.success) {
                setError(result.error || 'Action failed');
            }

            return result;
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
            setError(errorMessage);
            return {
                success: false,
                error: errorMessage,
                draftId: draft.id,
            };
        } finally {
            setIsExecuting(false);
        }
    }, []);

    const clearError = useCallback(() => {
        setError(null);
    }, []);

    return {
        isExecuting,
        error,
        executeAction,
        clearError,
    };
} 