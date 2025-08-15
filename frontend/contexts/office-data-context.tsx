"use client";

import { OfficeClient } from '@/api/clients/office-client';
import type { Contact } from '@/types/office-service';
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
    const officeClient = useMemo(() => new OfficeClient(), []);

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
            const resp = await officeClient.getContacts(providers, opts?.limit ?? 200, opts?.q, opts?.company, opts?.noCache);
            if (resp.success && resp.data) {
                setContacts((resp.data.contacts || []) as Contact[]);
            } else {
                setError('Failed to fetch contacts');
            }
        } catch (e: unknown) {
            setError((e && typeof e === 'object' && 'message' in e) ? (e as { message?: string }).message || 'Failed to load contacts' : 'Failed to load contacts');
        } finally {
            setLoading(false);
        }
    }, [officeClient]);

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