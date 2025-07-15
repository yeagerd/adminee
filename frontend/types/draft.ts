export type DraftType = 'email' | 'calendar' | 'document';

export type DraftStatus = 'draft' | 'ready' | 'sent' | 'archived';

export interface DraftMetadata {
    subject?: string;
    recipients?: string[];
    cc?: string[];
    bcc?: string[];
    startTime?: string;
    endTime?: string;
    location?: string;
    attendees?: string[];
    title?: string;
    tags?: string[];
    priority?: 'low' | 'medium' | 'high';
    applied_suggestions?: string[];
    ai_status?: 'pending' | 'approved' | 'rejected';
    ai_improved?: boolean;
    ai_confidence?: number;
    ai_prompt?: string;
    ai_context?: string;
    ai_improvement_prompt?: string;
    ai_rejection_reason?: string;
}

export interface Draft {
    id: string;
    type: DraftType;
    status: DraftStatus;
    content: string;
    metadata: DraftMetadata;
    isAIGenerated: boolean;
    createdAt: string;
    updatedAt: string;
    userId: string;
    threadId?: string; // For AI-generated drafts
}

export interface DraftState {
    currentDraft: Draft | null;
    draftList: Draft[];
    isLoading: boolean;
    error: string | null;
    autoSaveEnabled: boolean;
    lastAutoSave: string | null;
}

export interface DraftAction {
    type: 'SET_CURRENT_DRAFT' | 'UPDATE_DRAFT' | 'CLEAR_DRAFT' | 'SET_LOADING' | 'SET_ERROR' | 'SET_DRAFT_LIST' | 'ADD_DRAFT' | 'REMOVE_DRAFT';
    payload?: any;
}

export interface DraftEditorProps {
    draft: Draft;
    onUpdate: (draft: Draft) => void;
    onSave: () => void;
    onDiscard: () => void;
    onSend?: () => void;
    onCreate?: () => void;
}

export interface DraftMetadataProps {
    draft: Draft;
    onUpdate: (metadata: DraftMetadata) => void;
    type: DraftType;
} 