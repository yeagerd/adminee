/**
 * Bulk Action Type Definitions
 * 
 * This file provides the bulk action types that components expect.
 */

// Bulk action type enum
export enum BulkActionType {
    ARCHIVE = 'archive',
    DELETE = 'delete',
    SNOOZE = 'snooze',
    MARK_READ = 'mark_read',
    MARK_UNREAD = 'mark_unread',
    MOVE_TO_FOLDER = 'move_to_folder',
    APPLY_LABEL = 'apply_label',
    FORWARD = 'forward',
    REPLY = 'reply'
}

// Bulk action request
export interface BulkActionRequest {
    action: BulkActionType;
    message_ids: string[];
    folder_id?: string;
    label?: string;
    snooze_until?: string; // ISO string
}

// Bulk action response
export interface BulkActionResponse {
    success: boolean;
    processed_count: number;
    failed_count: number;
    failed_message_ids?: string[];
    error?: string;
}

// Type guard for runtime type checking
export function isBulkActionType(value: unknown): value is BulkActionType {
    return Object.values(BulkActionType).includes(value as BulkActionType);
}
