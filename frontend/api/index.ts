// Export base classes
export { GatewayClient } from './clients/gateway-client';
export { OfficeClient } from './clients/office-client';

// Export common types
export * from './types/common';

// Export service instances for convenience
import { OfficeClient } from './clients/office-client';
export const officeApi = new OfficeClient();
