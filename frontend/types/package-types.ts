/**
 * Package/Shipment Type Definitions
 * 
 * This file provides the package types that components expect, bridging the gap
 * between the generated OpenAPI types and the actual component requirements.
 */

// Package status enum - must match backend enum values exactly
export enum PackageStatus {
    PENDING = 'PENDING',
    IN_TRANSIT = 'IN_TRANSIT',
    OUT_FOR_DELIVERY = 'OUT_FOR_DELIVERY',
    DELIVERED = 'DELIVERED',
    EXCEPTION = 'EXCEPTION',
    DELAYED = 'DELAYED',
    CANCELLED = 'CANCELLED',
    RETURNED = 'RETURNED'
}

// Package structure
export interface Package {
    id: string;
    tracking_number: string;
    carrier: string;
    status: PackageStatus;
    recipient_name?: string;
    shipper_name?: string;
    package_description?: string;
    order_number?: string;
    tracking_link?: string;
    estimated_delivery?: string; // ISO string
    created_at: string; // ISO string
    updated_at: string; // ISO string
    archived_at?: string; // ISO string
}

// Package creation request
export interface PackageCreateRequest {
    tracking_number: string;
    carrier: string;
    status: PackageStatus;
    recipient_name?: string;
    shipper_name?: string;
    package_description?: string;
    order_number?: string;
    tracking_link?: string;
    expected_delivery?: string; // ISO string
}

// Package update request
export interface PackageUpdate {
    tracking_number?: string;
    carrier?: string;
    status?: PackageStatus;
    recipient_name?: string;
    shipper_name?: string;
    package_description?: string;
    order_number?: string;
    tracking_link?: string;
    estimated_delivery?: string; // ISO string
    archived_at?: string; // ISO string
}

// Tracking event structure
export interface TrackingEvent {
    id: string;
    event_date: string; // ISO string
    status: PackageStatus;
    location?: string;
    description?: string;
    created_at: string; // ISO string
}

// Tracking event creation request
export interface TrackingEventCreate {
    event_date: string; // ISO string
    status: PackageStatus;
    location?: string;
    description?: string;
    email_message_id?: string;
}

// Data collection request
export interface DataCollectionRequest {
    tracking_number: string;
    carrier: string;
    status: PackageStatus;
    recipient_name?: string;
    shipper_name?: string;
    package_description?: string;
    order_number?: string;
    tracking_link?: string;
    expected_delivery?: string; // ISO string
    user_consent: boolean;
    email_content?: string;
}

// Type guards for runtime type checking
export function isPackage(obj: unknown): obj is Package {
    return (
        typeof obj === 'object' &&
        obj !== null &&
        'id' in obj &&
        'tracking_number' in obj &&
        'carrier' in obj &&
        'status' in obj
    );
}

export function isTrackingEvent(obj: unknown): obj is TrackingEvent {
    return (
        typeof obj === 'object' &&
        obj !== null &&
        'id' in obj &&
        'event_date' in obj &&
        'status' in obj
    );
}

// Helper function to safely extract packages from API response
export function extractPackages(response: { packages?: unknown[] }): Package[] {
    if (!response.packages) {
        return [];
    }

    // Filter out any non-package objects
    return response.packages.filter(isPackage);
}

// Helper function to safely extract tracking events from API response
export function extractTrackingEvents(response: { events?: unknown[] }): TrackingEvent[] {
    if (!response.events) {
        return [];
    }

    // Filter out any non-tracking event objects
    return response.events.filter(isTrackingEvent);
}
