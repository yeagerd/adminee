/**
 * Email Type Definitions
 * 
 * This file provides the email types that components expect, bridging the gap
 * between the generated OpenAPI types and the actual component requirements.
 * 
 * The backend EmailMessage model has these properties:
 * - id, thread_id, subject, snippet, body_text, body_html
 * - from_address, to_addresses, cc_addresses, bcc_addresses
 * - date, labels, is_read, has_attachments
 * - provider, provider_message_id, account_email, account_name
 */

import type { Provider } from './api/office';

// Email address structure
export interface EmailAddress {
    email: string;
    name?: string;
}

// Core email message structure
export interface EmailMessage {
    id: string;
    thread_id?: string;
    subject?: string;
    snippet?: string;
    body_text?: string;
    body_html?: string;
    from_address?: EmailAddress;
    to_addresses: EmailAddress[];
    cc_addresses: EmailAddress[];
    bcc_addresses: EmailAddress[];
    date: string; // ISO string
    labels: string[];
    is_read: boolean;
    has_attachments: boolean;
    provider: Provider;
    provider_message_id: string;
    account_email: string;
    account_name?: string;
}

// Email thread structure
export interface EmailThread {
    id: string;
    subject?: string;
    messages: EmailMessage[];
    participant_count: number;
    last_message_date: string; // ISO string
    is_read: boolean;
    providers: Provider[];
}

// Email folder structure
export interface EmailFolder {
    label: string;
    name: string;
    provider: Provider;
    provider_folder_id?: string;
    account_email: string;
    account_name?: string;
    is_system: boolean;
    message_count?: number;
}

// Email filters for search/querying
export interface EmailFilters {
    labels?: string[];
    query?: string;
    from?: string;
    to?: string;
    has_attachments?: boolean;
    is_read?: boolean;
    date_from?: string;
    date_to?: string;
}

// Response wrapper types that match the generated API types
export interface EmailMessageListResponse {
    success: boolean;
    data?: EmailMessage[];
    error?: Record<string, unknown>;
    cache_hit?: boolean;
    provider_used?: Provider;
    request_id: string;
}

export interface EmailThreadListResponse {
    success: boolean;
    data?: EmailThread[];
    error?: Record<string, unknown>;
    cache_hit?: boolean;
    provider_used?: Provider;
    request_id: string;
}

export interface EmailFolderListResponse {
    success: boolean;
    data?: EmailFolder[];
    error?: Record<string, unknown>;
    cache_hit?: boolean;
    provider_used?: Provider;
    request_id: string;
}

// Utility type to extract the actual data from API responses
export type ExtractData<T> = T extends { data?: infer U } ? U : never;

// Type guards for runtime type checking
export function isEmailMessage(obj: unknown): obj is EmailMessage {
    return (
        typeof obj === 'object' &&
        obj !== null &&
        'id' in obj &&
        'date' in obj &&
        'provider' in obj &&
        'provider_message_id' in obj &&
        'account_email' in obj
    );
}

export function isEmailThread(obj: unknown): obj is EmailThread {
    return (
        typeof obj === 'object' &&
        obj !== null &&
        'id' in obj &&
        'messages' in obj &&
        Array.isArray((obj as any).messages)
    );
}

export function isEmailFolder(obj: unknown): obj is EmailFolder {
    return (
        typeof obj === 'object' &&
        obj !== null &&
        'label' in obj &&
        'name' in obj &&
        'provider' in obj &&
        'account_email' in obj
    );
}

// Helper function to safely extract email messages from API response
export function extractEmailMessages(response: EmailMessageListResponse): EmailMessage[] {
    if (!response.success || !response.data) {
        return [];
    }

    // Filter out any non-email message objects
    return response.data.filter(isEmailMessage);
}

// Helper function to safely extract email threads from API response
export function extractEmailThreads(response: EmailThreadListResponse): EmailThread[] {
    if (!response.success || !response.data) {
        return [];
    }

    // Filter out any non-email thread objects
    return response.data.filter(isEmailThread);
}

// Helper function to safely extract email folders from API response
export function extractEmailFolders(response: EmailFolderListResponse): EmailFolder[] {
    if (!response.success || !response.data) {
        return [];
    }

    // Filter out any non-email folder objects
    return response.data.filter(isEmailFolder);
}
