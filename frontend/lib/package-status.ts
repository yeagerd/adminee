// Package status constants - must match backend enum values
export const PACKAGE_STATUS = {
    PENDING: 'PENDING',
    IN_TRANSIT: 'IN_TRANSIT',
    OUT_FOR_DELIVERY: 'OUT_FOR_DELIVERY',
    DELIVERED: 'DELIVERED',
    EXCEPTION: 'EXCEPTION',
    DELAYED: 'DELAYED',
    CANCELLED: 'CANCELLED',
    RETURNED: 'RETURNED',
} as const;

export type PackageStatus = typeof PACKAGE_STATUS[keyof typeof PACKAGE_STATUS];

export const PACKAGE_STATUS_OPTIONS = [
    { value: PACKAGE_STATUS.PENDING, label: 'Pending' },
    { value: PACKAGE_STATUS.IN_TRANSIT, label: 'In Transit' },
    { value: PACKAGE_STATUS.OUT_FOR_DELIVERY, label: 'Out for Delivery' },
    { value: PACKAGE_STATUS.DELIVERED, label: 'Delivered' },
    { value: PACKAGE_STATUS.EXCEPTION, label: 'Exception' },
    { value: PACKAGE_STATUS.DELAYED, label: 'Delayed' },
    { value: PACKAGE_STATUS.CANCELLED, label: 'Cancelled' },
    { value: PACKAGE_STATUS.RETURNED, label: 'Returned' },
] as const;

// Status mapping for dashboard summary cards
export const DASHBOARD_STATUS_MAPPING = {
    [PACKAGE_STATUS.PENDING]: 'pending',
    [PACKAGE_STATUS.IN_TRANSIT]: 'shipped',
    [PACKAGE_STATUS.OUT_FOR_DELIVERY]: 'shipped',
    [PACKAGE_STATUS.DELIVERED]: 'delivered',
    [PACKAGE_STATUS.EXCEPTION]: 'late',
    [PACKAGE_STATUS.DELAYED]: 'late',
    [PACKAGE_STATUS.CANCELLED]: 'late',
    [PACKAGE_STATUS.RETURNED]: 'late',
} as const; 