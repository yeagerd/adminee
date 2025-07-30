import EmailFilters from '@/components/email/email-filters';
import { EmailFolderSelector } from '@/components/email/email-folder-selector';
import EmailThread from '@/components/email/email-thread';
import { useIntegrations } from '@/contexts/integrations-context';
import { gatewayClient } from '@/lib/gateway-client';
import { EmailFolder, EmailMessage } from '@/types/office-service';
import { ChevronLeft, ChevronRight, Grid3X3, List, RefreshCw, Settings } from 'lucide-react';
import { getSession } from 'next-auth/react';
import React, { useCallback, useEffect, useState } from 'react';

interface EmailViewProps {
    toolDataLoading?: boolean;
    activeTool?: string;
}

type ViewMode = 'tight' | 'expanded';
type ReadingPaneMode = 'none' | 'right';

const EmailView: React.FC<EmailViewProps> = ({ toolDataLoading = false, activeTool }) => {
    const [threads, setThreads] = useState<EmailMessage[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [filters, setFilters] = useState<Record<string, unknown>>({});
    const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
    const [viewMode, setViewMode] = useState<ViewMode>('tight');
    const [readingPaneMode, setReadingPaneMode] = useState<ReadingPaneMode>('right');
    const { loading: integrationsLoading, activeProviders, hasExpiredButRefreshableTokens } = useIntegrations();

    // Determine default provider from active integrations, fallback to 'google' if none available
    const defaultProvider = activeProviders && activeProviders.length > 0 ? activeProviders[0] as 'google' | 'microsoft' : 'google';

    const [selectedFolder, setSelectedFolder] = useState<EmailFolder>({
        label: 'inbox',
        name: 'Inbox',
        provider: defaultProvider,
        account_email: '',
        is_system: true
    });

    const fetchEmails = useCallback(async (noCache = false) => {
        if (!activeProviders || activeProviders.length === 0) {
            return;
        }

        try {
            const session = await getSession();
            const userId = session?.user?.id;
            if (!userId) throw new Error('No user id found in session');

            // For Microsoft, always use folder_id when available (both system and user folders)
            // For Google, use folder_id for system folders, labels for user folders
            const isSystemFolder = selectedFolder.is_system;
            let labels: string[] | undefined;
            let folderId: string | undefined;

            if (selectedFolder.provider === 'microsoft') {
                // Microsoft: use folder_id for all folders when available
                folderId = selectedFolder.provider_folder_id;
                labels = undefined;
            } else if (selectedFolder.provider === 'google') {
                // Google: use folder_id for system folders, labels for user folders
                if (isSystemFolder && selectedFolder.provider_folder_id) {
                    folderId = selectedFolder.provider_folder_id;
                    labels = undefined;
                } else {
                    labels = [selectedFolder.label];
                    folderId = undefined;
                }
            }

            const emailsResp = await gatewayClient.getEmails(activeProviders, 50, 0, noCache, labels, folderId) as { data?: { messages?: EmailMessage[] } };

            let messages = emailsResp.data?.messages || [];

            // Apply client-side filtering only for inbox and sent since we now use proper folder-specific fetching
            if (selectedFolder.label === 'inbox' || selectedFolder.label === 'sent') {
                const session = await getSession();
                const userEmail = session?.user?.email;
                if (userEmail) {
                    messages = messages.filter(msg => {
                        if (selectedFolder.label === 'inbox') {
                            // For inbox: show messages where user is recipient (in "to" field, not "from")
                            const isInToField = msg.to_addresses.some(addr => addr.email === userEmail);
                            const isFromUser = msg.from_address?.email === userEmail;
                            return isInToField && !isFromUser;
                        } else if (selectedFolder.label === 'sent') {
                            // For sent: show messages where user is sender (in "from" field)
                            const isFromUser = msg.from_address?.email === userEmail;
                            return isFromUser;
                        }
                        return true;
                    });
                }
            }

            setThreads(messages);
            setError(null);
        } catch (e: unknown) {
            setError((e && typeof e === 'object' && 'message' in e) ? (e as { message?: string }).message || 'Failed to load emails' : 'Failed to load emails');
        }
    }, [activeProviders, selectedFolder.label, selectedFolder.provider, selectedFolder.provider_folder_id, selectedFolder.is_system]);

    const handleRefresh = useCallback(async () => {
        setRefreshing(true);
        try {
            await fetchEmails(true); // Pass true to bypass cache
        } finally {
            setRefreshing(false);
        }
    }, [fetchEmails]);

    const handleFolderSelect = useCallback((folder: EmailFolder) => {
        setSelectedFolder(folder);
    }, []);

    const handleThreadSelect = useCallback((threadId: string) => {
        setSelectedThreadId(threadId);
    }, []);

    // Update selectedFolder provider when activeProviders change
    useEffect(() => {
        if (activeProviders && activeProviders.length > 0) {
            const newProvider = activeProviders[0] as 'google' | 'microsoft';
            if (selectedFolder.provider !== newProvider) {
                setSelectedFolder(prev => ({
                    ...prev,
                    provider: newProvider
                }));
            }
        }
    }, [activeProviders, selectedFolder.provider]);

    useEffect(() => {
        // Only fetch when the tab is actually activated
        if (toolDataLoading) return;
        if (integrationsLoading) return;
        if ((!activeProviders || activeProviders.length === 0)) {
            if (hasExpiredButRefreshableTokens) {
                setError('Your email integration token has expired and is being refreshed. Please wait or try reconnecting.');
            } else {
                setError('No active email integrations found. Please connect your email account first.');
            }
            setThreads([]);
            setLoading(false);
            return;
        }
        if (activeTool !== 'email') {
            setLoading(false);
            return;
        }

        let isMounted = true;
        setLoading(true);
        (async () => {
            try {
                await fetchEmails(false); // Use cached data for initial load
            } finally {
                if (isMounted) setLoading(false);
            }
        })();
        return () => { isMounted = false; };
    }, [filters, activeProviders, integrationsLoading, toolDataLoading, activeTool, hasExpiredButRefreshableTokens, fetchEmails, selectedFolder.label]);

    // Group emails by thread
    const groupedThreads = React.useMemo(() => {
        const threadMap = new Map<string, EmailMessage[]>();

        threads.forEach(email => {
            const threadId = email.thread_id || email.id;
            if (!threadMap.has(threadId)) {
                threadMap.set(threadId, []);
            }
            threadMap.get(threadId)!.push(email);
        });

        return Array.from(threadMap.entries()).map(([threadId, emails]) => ({
            id: threadId,
            emails
        }));
    }, [threads]);

    const selectedThread = selectedThreadId ? groupedThreads.find(t => t.id === selectedThreadId) : null;

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="p-4 border-b bg-white">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 flex-1">
                        <EmailFolderSelector
                            onFolderSelect={handleFolderSelect}
                            selectedFolder={selectedFolder}
                        />
                        <h1 className="text-xl font-semibold">{selectedFolder.name}</h1>
                        <div className="ml-4 flex-1 max-w-md">
                            <EmailFilters filters={filters} setFilters={setFilters} />
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        {/* View mode toggle */}
                        <div className="flex items-center border rounded-md">
                            <button
                                onClick={() => setViewMode('tight')}
                                className={`p-2 ${viewMode === 'tight' ? 'bg-blue-100 text-blue-600' : 'text-gray-600'}`}
                                title="Compact view"
                            >
                                <List className="w-4 h-4" />
                            </button>
                            <button
                                onClick={() => setViewMode('expanded')}
                                className={`p-2 ${viewMode === 'expanded' ? 'bg-blue-100 text-blue-600' : 'text-gray-600'}`}
                                title="Expanded view"
                            >
                                <Grid3X3 className="w-4 h-4" />
                            </button>
                        </div>

                        {/* Reading pane toggle */}
                        <div className="flex items-center border rounded-md">
                            <button
                                onClick={() => setReadingPaneMode('none')}
                                className={`p-2 ${readingPaneMode === 'none' ? 'bg-blue-100 text-blue-600' : 'text-gray-600'}`}
                                title="No reading pane"
                            >
                                <ChevronLeft className="w-4 h-4" />
                            </button>
                            <button
                                onClick={() => setReadingPaneMode('right')}
                                className={`p-2 ${readingPaneMode === 'right' ? 'bg-blue-100 text-blue-600' : 'text-gray-600'}`}
                                title="Reading pane on right"
                            >
                                <ChevronRight className="w-4 h-4" />
                            </button>
                        </div>

                        <button
                            onClick={handleRefresh}
                            disabled={refreshing || loading}
                            className="p-2 text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
                            title="Refresh emails"
                        >
                            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                        </button>

                        <button
                            className="p-2 text-muted-foreground hover:text-foreground transition-colors"
                            title="Settings"
                        >
                            <Settings className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            </div>

            {/* Main content */}
            <div className="flex-1 flex overflow-hidden">
                {/* Email list */}
                <div className={`flex-1 overflow-y-auto ${readingPaneMode === 'right' ? 'border-r' : ''}`}>
                    {loading ? (
                        <div className="p-8 text-center text-muted-foreground">Loading…</div>
                    ) : error ? (
                        <div className="p-8 text-center">
                            {error.includes('No active email integrations') ? (
                                <div className="text-amber-600">
                                    <p className="mb-4">No active email integration found. Connect your Gmail or Microsoft Outlook to view your emails.</p>
                                    <a
                                        href="/settings?page=integrations"
                                        className="inline-flex items-center gap-1 text-amber-700 hover:text-amber-900 font-medium"
                                    >
                                        <span>Go to Integrations</span>
                                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                        </svg>
                                    </a>
                                </div>
                            ) : error.includes('expired and is being refreshed') ? (
                                <div className="text-amber-600">
                                    <p className="mb-4">Your email integration token has expired and is being refreshed. Please wait or try reconnecting.</p>
                                    <a
                                        href="/settings?page=integrations"
                                        className="inline-flex items-center gap-1 text-amber-700 hover:text-amber-900 font-medium"
                                    >
                                        <span>Go to Integrations</span>
                                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                        </svg>
                                    </a>
                                </div>
                            ) : (
                                <div className="text-red-500">{error}</div>
                            )}
                        </div>
                    ) : groupedThreads.length === 0 ? (
                        <div className="p-8 text-center text-muted-foreground">No emails found.</div>
                    ) : (
                        <div className={viewMode === 'tight' ? '' : 'p-4'}>
                            {groupedThreads.map((thread) => (
                                <EmailThread
                                    key={thread.id}
                                    thread={thread}
                                    mode={viewMode}
                                    isSelected={selectedThreadId === thread.id}
                                    onSelect={handleThreadSelect}
                                    showReadingPane={readingPaneMode === 'right'}
                                />
                            ))}
                        </div>
                    )}
                </div>

                {/* Reading pane */}
                {readingPaneMode === 'right' && selectedThread && (
                    <div className="w-1/2 border-l bg-gray-50 overflow-y-auto">
                        <div className="p-4">
                            <h2 className="text-lg font-semibold mb-4">Reading Pane</h2>
                            <EmailThread
                                thread={selectedThread}
                                mode="expanded"
                                showReadingPane={true}
                            />
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default EmailView; 