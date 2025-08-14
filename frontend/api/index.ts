// Export base classes
export { GatewayClient } from './clients/gateway-client';
export { OfficeClient } from './clients/office-client';
export { ChatClient } from './clients/chat-client';

// Export common types
export * from './types/common';

// Export service instances for convenience
import { OfficeClient } from './clients/office-client';
import { ChatClient } from './clients/chat-client';
export const officeApi = new OfficeClient();
export const chatApi = new ChatClient();
