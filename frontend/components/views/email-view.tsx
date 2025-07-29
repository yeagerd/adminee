import { useIntegrations } from '@/contexts/integrations-context';
import { useDraftState } from '@/hooks/use-draft-state';
import type { EmailMessage } from '@/types/office-service';
import { RefreshCw } from 'lucide-react';
import { getSession } from 'next-auth/react';
import React, { useCallback, useEffect, useState } from 'react';
import gatewayClient from '../../lib/gateway-client';
import EmailFilters from '../email/email-filters';
import EmailThread from '../email/email-thread';

const OpenDraftPaneButton: React.FC = () => {
    const { createNewDraft } = useDraftState();
    const handleClick = async () => {
        const session = await getSession();
        const userId = session?.user?.id;
        if (userId) createNewDraft('email', userId);
        // Optionally, scroll to or focus the draft pane if needed
    };
    return (
        <button className="btn btn-primary" onClick={handleClick}>
            Compose Email
        </button>
    );
};

interface EmailViewProps {
    toolDataLoading?: boolean;
    activeTool?: string;
}

const EmailView: React.FC<EmailViewProps> = ({ toolDataLoading = false, activeTool }) => {
    const [threads, setThreads] = useState<EmailMessage[]>([]); // If API returns messages, not threads
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [filters, setFilters] = useState<Record<string, unknown>>({});
    const { loading: integrationsLoading, activeProviders, hasExpiredButRefreshableTokens } = useIntegrations();

    const fetchEmails = useCallback(async (noCache = false) => {
        if (!activeProviders || activeProviders.length === 0) {
            return;
        }

        try {
            const session = await getSession();
            const userId = session?.user?.id;
            if (!userId) throw new Error('No user id found in session');

            // Use the user's actual connected providers with no-cache flag
            const emailsResp = await gatewayClient.getEmails(activeProviders, 50, 0, noCache) as { data?: { messages?: EmailMessage[] } };
            setThreads(emailsResp.data?.messages || []);
            setError(null);
        } catch (e: unknown) {
            setError((e && typeof e === 'object' && 'message' in e) ? (e as { message?: string }).message || 'Failed to load emails' : 'Failed to load emails');
        }
    }, [activeProviders]);

    const handleRefresh = useCallback(async () => {
        setRefreshing(true);
        try {
            await fetchEmails(true); // Pass true to bypass cache
        } finally {
            setRefreshing(false);
        }
    }, [fetchEmails]);

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
        // Only fetch if there is at least one active email integration

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
    }, [filters, activeProviders, integrationsLoading, toolDataLoading, activeTool, hasExpiredButRefreshableTokens, fetchEmails]);

    return (
        <div className="flex flex-col h-full">
            <div className="p-4 border-b">
                <div className="flex items-center justify-between">
                    <h1 className="text-xl font-semibold">Inbox</h1>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={handleRefresh}
                            disabled={refreshing || loading}
                            className="p-2 text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
                            title="Refresh emails"
                        >
                            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                        </button>
                        <OpenDraftPaneButton />
                    </div>
                </div>
                <EmailFilters filters={filters} setFilters={setFilters} />
            </div>
            <div className="flex-1 overflow-y-auto">
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
                ) : threads.length === 0 ? (
                    <div className="p-8 text-center text-muted-foreground">No emails found.</div>
                ) : (
                    threads.map((thread: EmailMessage) => (
                        <EmailThread key={thread.id} thread={{ id: thread.id, emails: [thread] }} />
                    ))
                )}
            </div>
        </div>
    );
};

export default EmailView; 