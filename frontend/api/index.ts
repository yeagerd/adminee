// Export base classes
export { ChatClient } from './clients/chat-client';
export { MeetingsClient } from './clients/meetings-client';
export { OfficeClient } from './clients/office-client';

export { UserClient } from './clients/user-client';

// Export common types
export * from './types/common';

// Export shipments types
export * from './clients/shipments-client';

// Export service instances for convenience
import { ChatClient } from './clients/chat-client';
import { MeetingsClient } from './clients/meetings-client';
import { OfficeClient } from './clients/office-client';

import { ShipmentsClient } from './clients/shipments-client';
import { UserClient } from './clients/user-client';
export const officeApi = new OfficeClient();
export const chatApi = new ChatClient();
export const userApi = new UserClient();
export const meetingsApi = new MeetingsClient();
export const shipmentsApi = new ShipmentsClient();
