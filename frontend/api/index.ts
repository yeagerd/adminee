// Export base classes
export { BookingsClient } from './clients/bookings-client';
export { ChatClient } from './clients/chat-client';
export { ContactsClient } from './clients/contacts-client';
export { MeetingsClient } from './clients/meetings-client';
export { OfficeClient } from './clients/office-client';
export { UserClient } from './clients/user-client';

// Export types from clients
export * from './clients/bookings-client';

// Export common types
// Common types are now imported from generated types

// Export shipments types
export * from './clients/shipments-client';

// Export service instances for convenience
import { BookingsClient } from './clients/bookings-client';
import { ChatClient } from './clients/chat-client';
import { ContactsClient } from './clients/contacts-client';
import { MeetingsClient } from './clients/meetings-client';
import { OfficeClient } from './clients/office-client';
import { ShipmentsClient } from './clients/shipments-client';
import { UserClient } from './clients/user-client';

export const bookingsApi = new BookingsClient();
export const contactsApi = new ContactsClient();
export const chatApi = new ChatClient();
export const userApi = new UserClient();
export const meetingsApi = new MeetingsClient();
export const shipmentsApi = new ShipmentsClient();
