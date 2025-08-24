"use client";

import { officeApi, contactsApi } from '@/api';
import type { Contact } from '@/types/api/contacts';
import React, { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';

interface OfficeDataContextType {
    contacts: Contact[];
    loading: boolean;
    error: string | null;
    refreshContacts: (providers?: string[], opts?: { q?: string; company?: string; noCache?: boolean; limit?: number }) => Promise<void>;
    detectCompanyFromEmail: (email?: string) => string | undefined;
}

const OfficeDataContext = createContext<OfficeDataContextType | undefined>(undefined);

export const OfficeDataProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const lastQueryRef = useRef<{ providers?: string[]; q?: string; company?: string; limit?: number }>({});

    const detectCompanyFromEmail = useCallback((email?: string) => {
        if (!email) return undefined;
        const at = email.indexOf('@');
        if (at === -1) return undefined;
        const domain = email.slice(at + 1).toLowerCase();
        const parts = domain.split('.');
        const core = parts.length >= 2 ? parts[parts.length - 2] : parts[0];
        if (!core) return undefined;
        return core.charAt(0).toUpperCase() + core.slice(1);
    }, []);

    const refreshContacts = useCallback(async (providers?: string[], opts?: { q?: string; company?: string; noCache?: boolean; limit?: number }) => {
        setLoading(true);
        setError(null);
        try {
            lastQueryRef.current = { providers, q: opts?.q, company: opts?.company, limit: opts?.limit };
            
            // Use the new contacts API for fetching contacts
            // Convert old provider-based logic to new source_services logic
            let sourceServices: string[] | undefined;
            if (providers && providers.length > 0) {
                // Map old providers to new source services
                sourceServices = providers.map(provider => {
                    if (provider === 'google' || provider === 'microsoft') {
                        return 'office';
                    }
                    return provider;
                });
            }

            const resp = await contactsApi.getContacts(
                opts?.limit ?? 200,
                0, // offset
                undefined, // tags
                sourceServices,
                opts?.q // query
            );
            
            if (resp.success) {
                setContacts(resp.contacts || []);
            } else {
                setError('Failed to fetch contacts');
            }
        } catch (e: unknown) {
            setError((e && typeof e === 'object' && 'message' in e) ? (e as { message?: string }).message || 'Failed to load contacts' : 'Failed to load contacts');
        } finally {
            setLoading(false);
        }
    }, []);

    const value = useMemo(() => ({ contacts, loading, error, refreshContacts, detectCompanyFromEmail }), [contacts, loading, error, refreshContacts, detectCompanyFromEmail]);

    return (
        <OfficeDataContext.Provider value={value}>
            {children}
        </OfficeDataContext.Provider>
    );
};

export function useOfficeData() {
    const ctx = useContext(OfficeDataContext);
    if (!ctx) throw new Error('useOfficeData must be used within an OfficeDataProvider');
    return ctx;
}