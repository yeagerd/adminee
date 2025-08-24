/* 
 * Main types index for the frontend application.
 * This file exports commonly used types from various modules.
 */

// Re-export types from API modules
export type { EmailMessage } from './api/office/models/EmailMessage';

// Define types that are not in the generated API files
export type BulkActionType = 'mark_read' | 'mark_unread' | 'move_to_folder' | 'delete' | 'archive' | 'label';

// Re-export types from other modules
export * from './draft';
export * from './navigation';
export * from './package-types';
