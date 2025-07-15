import { AIDraftRequest, AIDraftResponse, aiDraftService, AIDraftSuggestion } from '@/services/ai-draft-service';
import { Draft } from '@/types/draft';
import { useCallback, useState } from 'react';

interface UseAIDraftsOptions {
    onDraftGenerated?: (draft: Draft) => void;
    onDraftImproved?: (draft: Draft) => void;
    onError?: (error: string) => void;
}

interface UseAIDraftsReturn {
    // State
    isGenerating: boolean;
    isImproving: boolean;
    currentSuggestions: AIDraftSuggestion[];
    lastGeneratedDraft: Draft | null;

    // Actions
    generateDraft: (request: AIDraftRequest) => Promise<Draft | null>;
    improveDraft: (draftId: string, improvementPrompt: string) => Promise<Draft | null>;
    generateSuggestions: (draft: Draft, context?: string) => Promise<AIDraftSuggestion[]>;
    approveAIDraft: (draftId: string) => Promise<void>;
    rejectAIDraft: (draftId: string, reason?: string) => Promise<void>;
    applySuggestion: (suggestion: AIDraftSuggestion, draft: Draft) => Promise<void>;
    clearSuggestions: () => void;
}

export function useAIDrafts(options: UseAIDraftsOptions = {}): UseAIDraftsReturn {
    const [isGenerating, setIsGenerating] = useState(false);
    const [isImproving, setIsImproving] = useState(false);
    const [currentSuggestions, setCurrentSuggestions] = useState<AIDraftSuggestion[]>([]);
    const [lastGeneratedDraft, setLastGeneratedDraft] = useState<Draft | null>(null);

    const generateDraft = useCallback(async (request: AIDraftRequest): Promise<Draft | null> => {
        try {
            setIsGenerating(true);

            const response: AIDraftResponse = await aiDraftService.generateDraft(request);

            setLastGeneratedDraft(response.draft);
            setCurrentSuggestions(response.suggestions);

            options.onDraftGenerated?.(response.draft);

            return response.draft;
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to generate AI draft';
            options.onError?.(errorMessage);
            return null;
        } finally {
            setIsGenerating(false);
        }
    }, [options]);

    const improveDraft = useCallback(async (draftId: string, improvementPrompt: string): Promise<Draft | null> => {
        try {
            setIsImproving(true);

            const response: AIDraftResponse = await aiDraftService.improveDraft(draftId, improvementPrompt);

            setLastGeneratedDraft(response.draft);
            setCurrentSuggestions(response.suggestions);

            options.onDraftImproved?.(response.draft);

            return response.draft;
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to improve draft';
            options.onError?.(errorMessage);
            return null;
        } finally {
            setIsImproving(false);
        }
    }, [options]);

    const generateSuggestions = useCallback(async (draft: Draft, context?: string): Promise<AIDraftSuggestion[]> => {
        try {
            const suggestions = await aiDraftService.generateSuggestions(draft, context);
            setCurrentSuggestions(suggestions);
            return suggestions;
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to generate suggestions';
            options.onError?.(errorMessage);
            return [];
        }
    }, [options]);

    const approveAIDraft = useCallback(async (draftId: string): Promise<void> => {
        try {
            await aiDraftService.approveAIDraft(draftId);
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to approve AI draft';
            options.onError?.(errorMessage);
        }
    }, [options]);

    const rejectAIDraft = useCallback(async (draftId: string, reason?: string): Promise<void> => {
        try {
            await aiDraftService.rejectAIDraft(draftId, reason);
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to reject AI draft';
            options.onError?.(errorMessage);
        }
    }, [options]);

    const applySuggestion = useCallback(async (suggestion: AIDraftSuggestion, draft: Draft): Promise<void> => {
        try {
            // This is a simplified implementation - in practice, you'd want to merge the suggestion
            // with the current draft content in a more sophisticated way
            if (suggestion.content) {
                // For now, just append the suggestion content
                const updatedContent = `${draft.content}\n\n${suggestion.content}`;

                // Update the draft through the gateway client
                const { gatewayClient } = await import('@/lib/gateway-client');
                await gatewayClient.updateDraft(draft.id, {
                    content: updatedContent,
                    metadata: {
                        ...draft.metadata,
                        applied_suggestions: [
                            ...(draft.metadata.applied_suggestions as string[] || []),
                            suggestion.id,
                        ],
                    },
                });
            }

            // Remove the applied suggestion from the current suggestions
            setCurrentSuggestions(prev => prev.filter(s => s.id !== suggestion.id));
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to apply suggestion';
            options.onError?.(errorMessage);
        }
    }, [options]);

    const clearSuggestions = useCallback(() => {
        setCurrentSuggestions([]);
    }, []);

    return {
        // State
        isGenerating,
        isImproving,
        currentSuggestions,
        lastGeneratedDraft,

        // Actions
        generateDraft,
        improveDraft,
        generateSuggestions,
        approveAIDraft,
        rejectAIDraft,
        applySuggestion,
        clearSuggestions,
    };
} 