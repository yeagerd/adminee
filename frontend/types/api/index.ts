// Auto-generated TypeScript types from OpenAPI schemas
// Generated on: 2025-01-24 09:33:33

// Core types (export from first service to avoid conflicts)
export * from './chat';

// Service-specific types (only unique models and services)
export type { Contact, ContactCreate, ContactListResponse, ContactResponse, ContactStatsResponse, EmailContactEventCount, EmailContactSearchResult, EmailContactUpdate } from './contacts';
export { ContactsService, InternalService } from './contacts';

export type { AvailabilityResponse } from './meetings';
export { BookingsService, EmailService, InvitationsService, PollsService, PublicService, SlotsService } from './meetings';

export { CalendarService, ContactsService as OfficeContactsService, EmailService as OfficeEmailService, FilesService, InternalBackfillService, InternalEmailService } from './office';

export { DefaultService as UserDefaultService } from './user';

export { CarriersService } from './shipments';
