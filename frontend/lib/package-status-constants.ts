import { PackageStatus } from '@/types/api/shipments';

// Package status options for select dropdowns
export const PACKAGE_STATUS_OPTIONS = [
    { value: PackageStatus.PENDING, label: 'Pending' },
    { value: PackageStatus.IN_TRANSIT, label: 'In Transit' },
    { value: PackageStatus.OUT_FOR_DELIVERY, label: 'Out for Delivery' },
    { value: PackageStatus.DELIVERED, label: 'Delivered' },
    { value: PackageStatus.EXCEPTION, label: 'Exception' },
    { value: PackageStatus.DELAYED, label: 'Delayed' },
    { value: PackageStatus.CANCELLED, label: 'Cancelled' },
    { value: PackageStatus.RETURNED, label: 'Returned' },
] as const;

// Status mapping for dashboard summary cards
export const DASHBOARD_STATUS_MAPPING = {
    [PackageStatus.PENDING]: 'pending',
    [PackageStatus.IN_TRANSIT]: 'shipped',
    [PackageStatus.OUT_FOR_DELIVERY]: 'shipped',
    [PackageStatus.DELIVERED]: 'delivered',
    [PackageStatus.EXCEPTION]: 'late',
    [PackageStatus.DELAYED]: 'late',
    [PackageStatus.CANCELLED]: 'late',
    [PackageStatus.RETURNED]: 'late',
} as const;
