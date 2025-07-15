'use client';

import { Draft, DraftAction, DraftMetadata, DraftState, DraftType } from '@/types/draft';
import { useCallback, useReducer } from 'react';

const initialState: DraftState = {
    currentDraft: null,
    draftList: [],
    isLoading: false,
    error: null,
    autoSaveEnabled: true,
    lastAutoSave: null,
};

function draftReducer(state: DraftState, action: DraftAction): DraftState {
    switch (action.type) {
        case 'SET_CURRENT_DRAFT':
            return {
                ...state,
                currentDraft: action.payload,
                error: null,
            };

        case 'UPDATE_DRAFT':
            if (!state.currentDraft) return state;
            return {
                ...state,
                currentDraft: {
                    ...state.currentDraft,
                    ...action.payload,
                    updatedAt: new Date().toISOString(),
                },
            };

        case 'CLEAR_DRAFT':
            return {
                ...state,
                currentDraft: null,
                error: null,
            };

        case 'SET_LOADING':
            return {
                ...state,
                isLoading: action.payload,
            };

        case 'SET_ERROR':
            return {
                ...state,
                error: action.payload,
                isLoading: false,
            };

        case 'SET_DRAFT_LIST':
            return {
                ...state,
                draftList: action.payload,
                isLoading: false,
            };

        case 'ADD_DRAFT':
            return {
                ...state,
                draftList: [...state.draftList, action.payload],
            };

        case 'REMOVE_DRAFT':
            return {
                ...state,
                draftList: state.draftList.filter(draft => draft.id !== action.payload),
            };

        default:
            return state;
    }
}

export function useDraftState() {
    const [state, dispatch] = useReducer(draftReducer, initialState);

    const setCurrentDraft = useCallback((draft: Draft | null) => {
        dispatch({ type: 'SET_CURRENT_DRAFT', payload: draft });
    }, []);

    const updateDraft = useCallback((updates: Partial<Draft>) => {
        dispatch({ type: 'UPDATE_DRAFT', payload: updates });
    }, []);

    const updateDraftContent = useCallback((content: string) => {
        dispatch({ type: 'UPDATE_DRAFT', payload: { content } });
    }, []);

    const updateDraftMetadata = useCallback((metadata: Partial<DraftMetadata>) => {
        dispatch({ type: 'UPDATE_DRAFT', payload: { metadata: { ...state.currentDraft?.metadata, ...metadata } } });
    }, [state.currentDraft?.metadata]);

    const clearDraft = useCallback(() => {
        dispatch({ type: 'CLEAR_DRAFT' });
    }, []);

    const setLoading = useCallback((loading: boolean) => {
        dispatch({ type: 'SET_LOADING', payload: loading });
    }, []);

    const setError = useCallback((error: string | null) => {
        dispatch({ type: 'SET_ERROR', payload: error });
    }, []);

    const setDraftList = useCallback((drafts: Draft[]) => {
        dispatch({ type: 'SET_DRAFT_LIST', payload: drafts });
    }, []);

    const addDraft = useCallback((draft: Draft) => {
        dispatch({ type: 'ADD_DRAFT', payload: draft });
    }, []);

    const removeDraft = useCallback((draftId: string) => {
        dispatch({ type: 'REMOVE_DRAFT', payload: draftId });
    }, []);

    const createNewDraft = useCallback((type: DraftType, userId: string) => {
        const newDraft: Draft = {
            id: `draft_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            type,
            status: 'draft',
            content: '',
            metadata: {},
            isAIGenerated: false,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            userId,
        };

        dispatch({ type: 'SET_CURRENT_DRAFT', payload: newDraft });
        dispatch({ type: 'ADD_DRAFT', payload: newDraft });

        return newDraft;
    }, []);

    return {
        state,
        setCurrentDraft,
        updateDraft,
        updateDraftContent,
        updateDraftMetadata,
        clearDraft,
        setLoading,
        setError,
        setDraftList,
        addDraft,
        removeDraft,
        createNewDraft,
    };
} 