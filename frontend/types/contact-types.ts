/**
 * Contact Type Definitions
 * 
 * This file provides the contact types that components expect, bridging the gap
 * between the generated OpenAPI types and the actual component requirements.
 */

import type { Provider } from './api/office';

// Contact structure
export interface Contact {
    id: string;
    name?: string;
    email?: string;
    phone?: string;
    company?: string;
    job_title?: string;
    notes?: string;
    provider: Provider;
    provider_contact_id: string;
    account_email: string;
    account_name?: string;
    created_at: string; // ISO string
    updated_at: string; // ISO string
}

// Contact list response wrapper
export interface ContactListResponse {
    success: boolean;
    data?: Contact[];
    error?: Record<string, unknown>;
    cache_hit?: boolean;
    provider_used?: Provider;
    request_id: string;
}

// Type guard for runtime type checking
export function isContact(obj: unknown): obj is Contact {
    return (
        typeof obj === 'object' &&
        obj !== null &&
        'id' in obj &&
        'provider' in obj &&
        'provider_contact_id' in obj &&
        'account_email' in obj
    );
}

// Helper function to safely extract contacts from API response
export function extractContacts(response: ContactListResponse): Contact[] {
    if (!response.success || !response.data) {
        return [];
    }

    // Filter out any non-contact objects
    return response.data.filter(isContact);
}
