// Auto-generated TypeScript types from OpenAPI schemas
// Generated on: 2025-01-24 09:33:33

// Core types (export from first service to avoid conflicts)
export * from './chat';

// Service-specific types (only unique models and services)
export { ContactsService, InternalService } from './contacts';
export type { Contact, ContactCreate, ContactListResponse, ContactResponse, ContactStatsResponse, EmailContactEventCount, EmailContactSearchResult, EmailContactUpdate } from './contacts';

export { BookingsService, EmailService, InvitationsService, PollsService, PublicService, SlotsService } from './meetings';
export type { AvailabilityResponse } from './meetings';

export { CalendarService, FilesService, InternalBackfillService, InternalEmailService, ContactsService as OfficeContactsService, EmailService as OfficeEmailService } from './office';

export { DefaultService as UserDefaultService } from './user';

export { CarriersService } from './shipments';
