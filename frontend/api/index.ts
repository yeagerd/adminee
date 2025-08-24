// Export base classes
export { BookingsClient } from './clients/bookings-client';
export { ChatClient } from './clients/chat-client';
export { MeetingsClient } from './clients/meetings-client';
export { OfficeClient } from './clients/office-client';
export { ContactsClient } from './clients/contacts-client';

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
import { MeetingsClient } from './clients/meetings-client';
import { OfficeClient } from './clients/office-client';

import { ShipmentsClient } from './clients/shipments-client';
import { UserClient } from './clients/user-client';
import { ContactsClient } from './clients/contacts-client';
export const bookingsApi = new BookingsClient();
export const officeApi = new OfficeClient();
export const chatApi = new ChatClient();
export const userApi = new UserClient();
export const meetingsApi = new MeetingsClient();
export const shipmentsApi = new ShipmentsClient();
export const contactsApi = new ContactsClient();
