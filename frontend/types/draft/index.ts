/* 
 * Draft types for the frontend application.
 * These types are re-exported from the API types for convenience.
 */

// Re-export draft types from the chat API
export type { DraftEmail } from '@/types/api/chat/models/DraftEmail';
export type { UserDraftResponse } from '@/types/api/chat/models/UserDraftResponse';
export type { UserDraftRequest } from '@/types/api/chat/models/UserDraftRequest';
export type { UserDraftListResponse } from '@/types/api/chat/models/UserDraftListResponse';
export type { DraftCalendarEvent } from '@/types/api/chat/models/DraftCalendarEvent';
export type { DraftCalendarChange } from '@/types/api/chat/models/DraftCalendarChange';

// Define additional draft types that components expect
export type Draft = UserDraftResponse;
export type DraftType = string;
export type DraftStatus = string;
export type DraftMetadata = Record<string, any>;
export type DraftAction = string;

// Draft state interface
export interface DraftState {
  draftList: Draft[];
  currentDraft: Draft | null;
  isLoading: boolean;
  error: string | null;
  autoSaveEnabled: boolean;
}

// Draft metadata props interface
export interface DraftMetadataProps {
  draft: Draft;
  onUpdate: (updates: Partial<Draft>) => void;
  type?: string;
}
