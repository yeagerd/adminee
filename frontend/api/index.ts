// Export base classes
export { GatewayClient } from './clients/gateway-client';
export { OfficeClient } from './clients/office-client';
export { ChatClient } from './clients/chat-client';
export { UserClient } from './clients/user-client';
export { MeetingsClient } from './clients/meetings-client';
export { ShipmentsClient } from './clients/shipments-client';

// Export common types
export * from './types/common';

// Export service instances for convenience
import { OfficeClient } from './clients/office-client';
import { ChatClient } from './clients/chat-client';
import { UserClient } from './clients/user-client';
import { MeetingsClient } from './clients/meetings-client';
import { ShipmentsClient } from './clients/shipments-client';
export const officeApi = new OfficeClient();
export const chatApi = new ChatClient();
export const userApi = new UserClient();
export const meetingsApi = new MeetingsClient();
export const shipmentsApi = new ShipmentsClient();
