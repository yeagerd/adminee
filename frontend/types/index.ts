/**
 * Main Type Definitions Index
 * 
 * This file exports all the custom type definitions that bridge the gap
 * between generated OpenAPI types and component requirements.
 */

// Email types
export * from './email-types';

// Contact types
export * from './contact-types';

// Package/Shipment types
export * from './package-types';

// Bulk action types
export * from './bulk-action-types';

// Re-export commonly used generated types
export type { UserDraftRequest, UserDraftResponse } from './api/chat';
export { Provider } from './api/office';
export type { CalendarEvent, CalendarEventResponse } from './api/office';

