import { contactsApi } from '@/api';
import SourceFilter from '@/components/contacts/source-filter';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useIntegrations } from '@/contexts/integrations-context';
import type { Contact } from "@/types/api/contacts";
import { BarChart3, Plus, RefreshCw, Settings } from 'lucide-react';
import { getSession } from 'next-auth/react';
import React, { useCallback, useEffect, useMemo, useState } from 'react';

interface ContactsViewProps {
    toolDataLoading?: boolean;
    activeTool?: string;
}

const ContactsView: React.FC<ContactsViewProps> = ({ toolDataLoading = false, activeTool }) => {
    const { loading: integrationsLoading, activeProviders } = useIntegrations();
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [search, setSearch] = useState('');
    const [sourceFilter, setSourceFilter] = useState<string[]>([]);
    const [tagFilter, setTagFilter] = useState<string[]>([]);

    const fetchContacts = useCallback(async (noCache = false) => {
        try {
            const session = await getSession();
            const userId = session?.user?.id;
            if (!userId) throw new Error('No user id found in session');

            // Use source filter array directly - empty array means all sources
            const sourceServices = sourceFilter.length > 0 ? sourceFilter : undefined;

            const resp = await contactsApi.getContacts(
                200, // limit
                0,   // offset
                tagFilter.length > 0 ? tagFilter : undefined,
                sourceServices,
                search || undefined
            );

            if (resp.success) {
                setContacts(resp.contacts);
                setError(null);
            } else {
                setError('Failed to fetch contacts');
            }
        } catch (e: unknown) {
            setError((e && typeof e === 'object' && 'message' in e) ? (e as { message?: string }).message || 'Failed to load contacts' : 'Failed to load contacts');
        }
    }, [search, sourceFilter, tagFilter]);

    const handleRefresh = useCallback(async () => {
        setRefreshing(true);
        try {
            await fetchContacts(true);
        } finally {
            setRefreshing(false);
        }
    }, [fetchContacts]);

    useEffect(() => {
        if (toolDataLoading || integrationsLoading) return;
        if (activeTool !== 'contacts') {
            setLoading(false);
            return;
        }

        let mounted = true;
        setLoading(true);
        (async () => {
            try { await fetchContacts(false); } finally { if (mounted) setLoading(false); }
        })();
        return () => { mounted = false; };
    }, [integrationsLoading, toolDataLoading, activeTool, fetchContacts]);

    // Use contacts directly since we removed relevance filtering
    const filteredContacts = contacts;

    // Get unique tags from contacts
    const allTags = useMemo(() => {
        const tagSet = new Set<string>();
        contacts.forEach(contact => {
            if (contact.tags) {
                contact.tags.forEach(tag => tagSet.add(tag));
            }
        });
        return Array.from(tagSet).sort();
    }, [contacts]);

    // Get available source services from contacts
    const availableSources = useMemo(() => {
        const sourceSet = new Set<string>();
        contacts.forEach(contact => {
            if (contact.source_services) {
                contact.source_services.forEach(service => sourceSet.add(service));
            }
        });
        return Array.from(sourceSet).sort();
    }, [contacts]);

    // Get provider information for contacts
    const providerInfo = useMemo(() => {
        const info: Record<string, string> = {};
        contacts.forEach(contact => {
            if (contact.source_services?.includes('contacts') && contact.provider) {
                info['contacts'] = contact.provider;
            }
        });
        return info;
    }, [contacts]);

    // Get source service statistics
    const sourceStats = useMemo(() => {
        const stats = { contacts: 0, discovered: 0, both: 0 };
        contacts.forEach(contact => {
            const hasContacts = contact.source_services?.includes('contacts') || false;
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

    return (
        <div className="flex flex-col h-full">
            <div className="p-4 border-b bg-white">
                <div className="flex items-center gap-3">
                    <h1 className="text-xl font-semibold">Contacts</h1>
                    <div className="flex items-center gap-2 ml-4">
                        <Input
                            placeholder="Search name, email, or notes"
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            className="w-64"
                        />

                        {/* Source Filter */}
                        <SourceFilter
                            sourceFilter={sourceFilter}
                            onSourceFilterChange={setSourceFilter}
                            availableSources={availableSources}
                            providerInfo={providerInfo}
                        />

                        {/* Tags Filter */}
                        <select
                            value={tagFilter}
                            onChange={(e) => {
                                const selectedOptions = Array.from(e.target.selectedOptions, option => option.value);
                                setTagFilter(selectedOptions);
                            }}
                            className="border rounded px-2 py-1 text-sm"
                            multiple
                        >
                            <option value="">All Tags</option>
                            {allTags.map(tag => (
                                <option key={tag} value={tag}>{tag}</option>
                            ))}
                        </select>



                        <Button variant="ghost" size="sm" onClick={handleRefresh} disabled={refreshing || loading} title="Refresh">
                            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                        </Button>

                        <Button variant="outline" size="sm" title="Add Contact">
                            <Plus className="w-4 h-4" />
                        </Button>

                        <Button variant="outline" size="sm" title="Discovery Settings">
                            <Settings className="w-4 h-4" />
                        </Button>

                        <Button variant="outline" size="sm" title="Analytics">
                            <BarChart3 className="w-4 h-4" />
                        </Button>
                    </div>
                </div>

                {/* Source Statistics */}
                <div className="flex gap-4 mt-3 text-sm text-gray-600">
                    <span>Total: {contacts.length}</span>
                                            <span>Contacts: {sourceStats.contacts}</span>
                    <span>Discovered: {sourceStats.discovered}</span>
                    <span>Both: {sourceStats.both}</span>
                </div>
            </div>

            <div className="flex-1 overflow-auto">
                {loading ? (
                    <div className="p-8 text-center text-muted-foreground">Loading…</div>
                ) : error ? (
                    <div className="p-8 text-center text-red-500">{error}</div>
                ) : filteredContacts.length === 0 ? (
                    <div className="p-8 text-center text-muted-foreground">No contacts found.</div>
                ) : (
                    <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {filteredContacts.map((contact) => (
                            <div key={contact.id} className="bg-white border rounded p-3 shadow-sm">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center text-gray-600 text-sm">
                                        {(contact.display_name || contact.email_address || '').slice(0, 1).toUpperCase()}
                                    </div>
                                    <div className="min-w-0 flex-1">
                                        <div className="font-medium truncate">
                                            {contact.display_name || contact.email_address}
                                        </div>
                                        <div className="text-sm text-gray-500 truncate">
                                            {contact.email_address}
                                        </div>

                                        {/* Source Services Badges */}
                                        <div className="flex gap-1 mt-1">
                                            {contact.source_services?.map(service => (
                                                <span
                                                    key={service}
                                                    className={`px-2 py-1 text-xs rounded-full ${service === 'office' ? 'bg-blue-100 text-blue-800' :
                                                        service === 'email' ? 'bg-green-100 text-green-800' :
                                                            service === 'calendar' ? 'bg-purple-100 text-purple-800' :
                                                                service === 'documents' ? 'bg-orange-100 text-orange-800' :
                                                                    'bg-gray-100 text-gray-800'
                                                        }`}
                                                >
                                                    {service}
                                                </span>
                                            ))}
                                        </div>



                                        {/* Event Counts */}
                                        {contact.event_counts && Object.keys(contact.event_counts).length > 0 && (
                                            <div className="flex gap-2 mt-1">
                                                {Object.entries(contact.event_counts).map(([eventType, count]) => (
                                                    <span key={eventType} className="text-xs text-gray-500">
                                                        {eventType}: {count.count}
                                                    </span>
                                                ))}
                                            </div>
                                        )}

                                        {/* Tags */}
                                        {contact.tags && contact.tags.length > 0 && (
                                            <div className="flex gap-1 mt-1">
                                                {contact.tags.slice(0, 3).map(tag => (
                                                    <span key={tag} className="px-1 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">
                                                        {tag}
                                                    </span>
                                                ))}
                                                {contact.tags.length > 3 && (
                                                    <span className="px-1 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">
                                                        +{contact.tags.length - 3}
                                                    </span>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default ContactsView;