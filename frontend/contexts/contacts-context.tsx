'use client';

import { contactsApi } from '@/api';
import { Contact } from '@/types/contacts';
import { getSession } from 'next-auth/react';
import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';

interface ContactsContextType {
    contacts: Contact[];
    loading: boolean;
    error: string | null;
    refreshContacts: () => Promise<void>;
    filterContacts: (filters: ContactFilters) => Contact[];
    availableSources: string[];
    sourceStats: { contacts: number; discovered: number; both: number };
}

interface ContactFilters {
    search?: string;
    sourceServices?: string[];
    tags?: string[];
}

const ContactsContext = createContext<ContactsContextType | undefined>(undefined);

export const useContacts = () => {
    const context = useContext(ContactsContext);
    if (!context) {
        throw new Error('useContacts must be used within a ContactsProvider');
    }
    return context;
};

export const ContactsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchContacts = useCallback(async (noCache = false) => {
        try {
            setLoading(true);
            setError(null);

            const session = await getSession();
            const userId = session?.user?.id;
            if (!userId) throw new Error('No user id found in session');

            const resp = await contactsApi.getContacts(
                200, // limit
                0,   // offset
                undefined, // tags - we'll filter client-side
                undefined, // source_services - we'll filter client-side
                undefined  // search - we'll filter client-side
            );

            if (resp.success) {
                setContacts(resp.contacts);
            } else {
                setError('Failed to fetch contacts');
            }
        } catch (e: unknown) {
            setError((e && typeof e === 'object' && 'message' in e) ? (e as { message?: string }).message || 'Failed to load contacts' : 'Failed to load contacts');
        } finally {
            setLoading(false);
        }
    }, []);

    const refreshContacts = useCallback(async () => {
        await fetchContacts(true);
    }, [fetchContacts]);

    // Get available source services from contacts (with backward compatibility)
    const availableSources = React.useMemo(() => {
        const sourceSet = new Set<string>();
        contacts.forEach(contact => {
            if (contact.source_services) {
                contact.source_services.forEach(service => {
                    // Map 'office' to 'contacts' for backward compatibility
                    const mappedService = service === 'office' ? 'contacts' : service;
                    sourceSet.add(mappedService);
                });
            }
        });
        return Array.from(sourceSet).sort();
    }, [contacts]);

    // Get source service statistics
    const sourceStats = React.useMemo(() => {
        const stats = { contacts: 0, discovered: 0, both: 0 };
        contacts.forEach(contact => {
            const hasContacts = contact.source_services?.some(s => s === 'office' || s === 'contacts') || false;
            const hasDiscovered = contact.source_services?.some(s => ['email', 'calendar', 'documents'].includes(s)) || false;

            if (hasContacts && hasDiscovered) {
                stats.both++;
            } else if (hasContacts) {
                stats.contacts++;
            } else if (hasDiscovered) {
                stats.discovered++;
            }
        });
        return stats;
    }, [contacts]);

    // Client-side filtering function
    const filterContacts = useCallback((filters: ContactFilters): Contact[] => {
        let filtered = [...contacts];

        // Filter by search
        if (filters.search) {
            const searchLower = filters.search.toLowerCase();
            filtered = filtered.filter(contact =>
                contact.display_name?.toLowerCase().includes(searchLower) ||
                contact.email_address?.toLowerCase().includes(searchLower) ||
                contact.notes?.toLowerCase().includes(searchLower)
            );
        }

        // Filter by source services
        // Semantics:
        // - undefined => no filtering (show all)
        // - [] => explicit empty selection (show none)
        if (Array.isArray(filters.sourceServices)) {
            // If explicitly an empty array, return empty set immediately
            if (filters.sourceServices.length === 0) {
                return [];
            }
            filtered = filtered.filter(contact => {
                if (!contact.source_services) return false;
                return filters.sourceServices!.some(filterService => {
                    // Handle backward compatibility: 'contacts' should match both 'contacts' and 'office'
                    if (filterService === 'contacts') {
                        return contact.source_services!.some(s => s === 'contacts' || s === 'office');
                    }
                    return contact.source_services!.includes(filterService);
                });
            });
        }

        // Filter by tags
        if (filters.tags && filters.tags.length > 0) {
            filtered = filtered.filter(contact => {
                if (!contact.tags) return false;
                return filters.tags!.some(tag => contact.tags!.includes(tag));
            });
        }

        return filtered;
    }, [contacts]);

    // Load contacts on mount
    useEffect(() => {
        fetchContacts();
    }, [fetchContacts]);

    const value: ContactsContextType = {
        contacts,
        loading,
        error,
        refreshContacts,
        filterContacts,
        availableSources,
        sourceStats,
    };

    return (
        <ContactsContext.Provider value={value}>
            {children}
        </ContactsContext.Provider>
    );
};
