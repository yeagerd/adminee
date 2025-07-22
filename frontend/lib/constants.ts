// Integration status constants - must match backend enum values
export const INTEGRATION_STATUS = {
    ACTIVE: 'active',
    INACTIVE: 'inactive',
    ERROR: 'error',
    PENDING: 'pending',
    EXPIRED: 'expired',
} as const;

export type IntegrationStatus = typeof INTEGRATION_STATUS[keyof typeof INTEGRATION_STATUS];

// Integration provider constants
export const INTEGRATION_PROVIDER = {
    GOOGLE: 'google',
    MICROSOFT: 'microsoft',
    SLACK: 'slack',
} as const;

export type IntegrationProvider = typeof INTEGRATION_PROVIDER[keyof typeof INTEGRATION_PROVIDER]; 