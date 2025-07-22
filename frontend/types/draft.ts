export type DraftType = 'email' | 'calendar' | 'document' | 'calendar_event' | 'calendar_change';

export type DraftStatus = 'draft' | 'ready' | 'sent' | 'archived';

export interface DraftMetadata {
    subject?: string;
    recipients?: string[];
    cc?: string[];
    bcc?: string[];
    startTime?: string | (() => string);
    endTime?: string | (() => string);
    location?: string;
    attendees?: string[];
    title?: string;
    tags?: string[];
    priority?: 'low' | 'medium' | 'high';
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