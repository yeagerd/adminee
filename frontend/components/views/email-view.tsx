import EmailFilters from '@/components/email/email-filters';
import { EmailFolderSelector } from '@/components/email/email-folder-selector';
import EmailListCard from '@/components/email/email-list-card';
import EmailThread from '@/components/email/email-thread';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { useIntegrations } from '@/contexts/integrations-context';
import { gatewayClient } from '@/lib/gateway-client';
import { safeParseDate } from '@/lib/utils';
import { EmailFolder, EmailMessage, EmailThread as EmailThreadType } from '@/types/office-service';
import { Archive, Check, ChevronLeft, Clock, List, ListTodo, PanelLeft, RefreshCw, Settings, Square, Trash2, X } from 'lucide-react';
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
    const [fullThread, setFullThread] = useState<EmailThreadType | null>(null);
    const [loadingThread, setLoadingThread] = useState(false);
    const [threadError, setThreadError] = useState<string | null>(null);
    const [viewMode, setViewMode] = useState<ViewMode>('tight');
    const [readingPaneMode, setReadingPaneMode] = useState<ReadingPaneMode>('right');
    const [settingsOpen, setSettingsOpen] = useState(false);
    const [isInThreadView, setIsInThreadView] = useState(false);
    const [selectedEmails, setSelectedEmails] = useState<Set<string>>(new Set());
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
            // Clear email selections when emails are fetched/updated
            setSelectedEmails(new Set());
        } catch (e: unknown) {
            setError((e && typeof e === 'object' && 'message' in e) ? (e as { message?: string }).message || 'Failed to load emails' : 'Failed to load emails');
        }
    }, [activeProviders, selectedFolder.label, selectedFolder.provider, selectedFolder.provider_folder_id, selectedFolder.is_system]);

    const handleRefresh = useCallback(async () => {
        setRefreshing(true);
        try {
            await fetchEmails(true); // Pass true to bypass cache
            // Clear email selections after refresh
            setSelectedEmails(new Set());
        } finally {
            setRefreshing(false);
        }
    }, [fetchEmails]);

    const handleFolderSelect = useCallback((folder: EmailFolder) => {
        setSelectedFolder(folder);
        // Clear email selections when folder changes
        setSelectedEmails(new Set());
    }, []);

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
            // Sort emails by date (latest first) so that emails[0] is always the latest email
            // Use safeParseDate to handle invalid dates gracefully
            emails: emails.sort((a, b) => {
                const dateA = safeParseDate(a.date);
                const dateB = safeParseDate(b.date);

                // If both dates are invalid, maintain original order
                if (!dateA && !dateB) return 0;
                // If only dateA is invalid, put it at the end
                if (!dateA) return 1;
                // If only dateB is invalid, put it at the end
                if (!dateB) return -1;

                // Both dates are valid, compare them
                return dateB.getTime() - dateA.getTime();
            })
        }));
    }, [threads]);

    // Handle select all emails in current view
    const handleSelectAll = useCallback(() => {
        const allEmailIds = new Set<string>();
        groupedThreads.forEach(thread => {
            if (viewMode === 'tight') {
                // In tight view mode, only select the latest email in each thread
                // since that's the only one with a visible checkbox
                const latestEmail = thread.emails[0]; // Assuming emails are sorted by date, latest first
                if (latestEmail) {
                    allEmailIds.add(latestEmail.id);
                }
            } else {
                // In expanded view mode, select all emails in each thread
                thread.emails.forEach(email => {
                    allEmailIds.add(email.id);
                });
            }
        });
        setSelectedEmails(allEmailIds);
    }, [groupedThreads, viewMode]);

    // Handle deselect all emails
    const handleSelectNone = useCallback(() => {
        setSelectedEmails(new Set());
    }, []);

    // Handle bulk actions
    const handleBulkArchive = useCallback(() => {
        // TODO: Implement bulk archive functionality
        console.log('Archive emails:', Array.from(selectedEmails));
        setSelectedEmails(new Set()); // Clear selection after action
    }, [selectedEmails]);

    const handleBulkDelete = useCallback(() => {
        // TODO: Implement bulk delete functionality
        console.log('Delete emails:', Array.from(selectedEmails));
        setSelectedEmails(new Set()); // Clear selection after action
    }, [selectedEmails]);

    const handleBulkSnooze = useCallback(() => {
        // TODO: Implement bulk snooze functionality
        console.log('Snooze emails:', Array.from(selectedEmails));
        setSelectedEmails(new Set()); // Clear selection after action
    }, [selectedEmails]);

    // selectedThread was used for fallback logic that has been removed
    // Keeping this for potential future use or debugging

    // Function to fetch full thread when user clicks into it
    const fetchFullThread = useCallback(async (threadId: string) => {
        setLoadingThread(true);
        setThreadError(null);

        try {
            const response = await gatewayClient.getThread(threadId, true); // include body
            if (response.data?.thread) {
                setFullThread(response.data.thread);
            } else {
                throw new Error('No thread data received from API');
            }
        } catch (error) {
            console.error('Error fetching full thread:', error);
            setThreadError('Failed to load thread data. Please try refreshing.');
            setFullThread(null);
        } finally {
            setLoadingThread(false);
        }
    }, []);

    const handleThreadSelect = useCallback((threadId: string) => {
        setSelectedThreadId(threadId);
        // Clear the previous thread data immediately
        setFullThread(null);
        // Fetch full thread when user clicks into it
        fetchFullThread(threadId);

        // Handle click behavior based on pane mode
        if (readingPaneMode === 'none') {
            // One-pane mode: navigate to thread view
            setIsInThreadView(true);
        }
        // Two-pane mode: thread will be shown in right pane automatically
    }, [readingPaneMode, fetchFullThread]);

    const handleBackToList = useCallback(() => {
        setIsInThreadView(false);
        setSelectedThreadId(null);
        setFullThread(null);
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

    // Reset thread view when reading pane mode changes
    useEffect(() => {
        if (readingPaneMode === 'right') {
            // When switching to two-pane mode, exit thread view
            setIsInThreadView(false);
        }
    }, [readingPaneMode]);



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
                        <button
                            onClick={handleRefresh}
                            disabled={refreshing || loading}
                            className="p-2 text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
                            title="Refresh emails"
                        >
                            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                        </button>

                        {/* Settings dropdown */}
                        <DropdownMenu open={settingsOpen} onOpenChange={setSettingsOpen}>
                            <DropdownMenuTrigger asChild>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="p-2 text-muted-foreground hover:text-foreground transition-colors"
                                    title="Settings"
                                >
                                    <Settings className="w-4 h-4" />
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="w-64">
                                {/* Email Card View Mode */}
                                <DropdownMenuItem className="flex items-center justify-between p-3">
                                    <span className="text-sm font-medium">Email Card View</span>
                                    <div className="flex items-center border rounded-md">
                                        <button
                                            onClick={() => { setViewMode('tight'); setSettingsOpen(false); }}
                                            className={`p-1.5 ${viewMode === 'tight' ? 'bg-blue-100 text-blue-600' : 'text-gray-600'}`}
                                            title="Compact view"
                                        >
                                            <List className="w-3 h-3" />
                                        </button>
                                        <button
                                            onClick={() => { setViewMode('expanded'); setSettingsOpen(false); }}
                                            className={`p-1.5 ${viewMode === 'expanded' ? 'bg-blue-100 text-blue-600' : 'text-gray-600'}`}
                                            title="Expanded view"
                                        >
                                            <ListTodo className="w-3 h-3" />
                                        </button>
                                    </div>
                                </DropdownMenuItem>

                                <DropdownMenuSeparator />

                                {/* Reading Pane Mode */}
                                <DropdownMenuItem className="flex items-center justify-between p-3">
                                    <span className="text-sm font-medium">Reading Pane</span>
                                    <div className="flex items-center border rounded-md">
                                        <button
                                            onClick={() => {
                                                setReadingPaneMode('none');
                                                setSettingsOpen(false);
                                                setSelectedThreadId(null); // Clear selection when switching to one-pane
                                            }}
                                            className={`p-1.5 ${readingPaneMode === 'none' ? 'bg-blue-100 text-blue-600' : 'text-gray-600'}`}
                                            title="No reading pane"
                                        >
                                            <Square className="w-3 h-3" />
                                        </button>
                                        <button
                                            onClick={() => {
                                                setReadingPaneMode('right');
                                                setSettingsOpen(false);
                                            }}
                                            className={`p-1.5 ${readingPaneMode === 'right' ? 'bg-blue-100 text-blue-600' : 'text-gray-600'}`}
                                            title="Reading pane on right"
                                        >
                                            <PanelLeft className="w-3 h-3" />
                                        </button>
                                    </div>
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    </div>
                </div>
            </div>

            {/* Main content */}
            <div className="flex-1 flex overflow-hidden">
                {/* Email list or Thread view */}
                {isInThreadView && readingPaneMode === 'none' ? (
                    // One-pane thread view - show EmailCard for full email content
                    <div className="flex-1 overflow-y-auto">
                        {selectedThreadId && (
                            <div className="p-4">
                                <div className="flex items-center gap-3 mb-4">
                                    <button
                                        onClick={handleBackToList}
                                        className="p-2 text-muted-foreground hover:text-foreground transition-colors"
                                        title="Back to email list"
                                    >
                                        <ChevronLeft className="w-4 h-4" />
                                    </button>
                                    <h2 className="text-lg font-semibold">Thread</h2>
                                </div>
                                {loadingThread ? (
                                    <div className="p-8 text-center text-muted-foreground">Loading thread...</div>
                                ) : threadError ? (
                                    <div className="p-8 text-center text-red-500">
                                        {threadError}
                                    </div>
                                ) : fullThread ? (
                                    <EmailThread
                                        thread={fullThread}
                                    />
                                ) : (
                                    <div className="p-8 text-center text-muted-foreground">
                                        No thread data available
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                ) : (
                    // Email list (for both two-pane and one-pane modes)
                    <div className={`flex-1 flex flex-col overflow-y-auto ${readingPaneMode === 'right' ? 'border-r' : ''}`} style={{ minWidth: 0 }}>
                        {/* Selection Header */}
                        {selectedEmails.size > 0 && (
                            <div className="bg-blue-50 border-b border-blue-200 px-4 py-3">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-4">
                                        <span className="text-sm font-medium text-blue-900">
                                            {selectedEmails.size} email{selectedEmails.size !== 1 ? 's' : ''} selected
                                        </span>
                                        <div className="flex items-center gap-2">
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={handleSelectNone}
                                                className="text-blue-700 hover:text-blue-900 hover:bg-blue-100"
                                            >
                                                <X className="w-4 h-4 mr-1" />
                                                None
                                            </Button>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={handleSelectAll}
                                                className="text-blue-700 hover:text-blue-900 hover:bg-blue-100"
                                            >
                                                <Check className="w-4 h-4 mr-1" />
                                                All
                                            </Button>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={handleBulkSnooze}
                                            className="text-blue-700 hover:text-blue-900 hover:bg-blue-100"
                                            title="Snooze"
                                        >
                                            <Clock className="w-4 h-4" />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={handleBulkArchive}
                                            className="text-blue-700 hover:text-blue-900 hover:bg-blue-100"
                                            title="Archive"
                                        >
                                            <Archive className="w-4 h-4" />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={handleBulkDelete}
                                            className="text-red-700 hover:text-red-900 hover:bg-red-100"
                                            title="Delete"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        )}

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
                                    <EmailListCard
                                        key={thread.id}
                                        thread={thread}
                                        mode={viewMode}
                                        isSelected={selectedThreadId === thread.id}
                                        onSelect={handleThreadSelect}
                                        showReadingPane={false}
                                        selectedEmails={selectedEmails}
                                        onEmailSelect={(emailId: string, selected: boolean) => {
                                            setSelectedEmails(prev => {
                                                const newSet = new Set(prev);
                                                if (selected) {
                                                    newSet.add(emailId);
                                                } else {
                                                    newSet.delete(emailId);
                                                }
                                                return newSet;
                                            });
                                        }}
                                    />
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Reading pane */}
                {readingPaneMode === 'right' && selectedThreadId && (
                    <div className="flex-1 border-l bg-gray-50 overflow-y-auto" style={{ minWidth: 0 }}>
                        <div className="p-4">
                            {loadingThread ? (
                                <div className="p-8 text-center text-muted-foreground">Loading thread...</div>
                            ) : threadError ? (
                                <div className="p-8 text-center text-red-500">
                                    {threadError}
                                </div>
                            ) : fullThread ? (
                                <EmailThread
                                    thread={fullThread}
                                />
                            ) : (
                                <div className="p-8 text-center text-muted-foreground">
                                    No thread data available
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default EmailView; 