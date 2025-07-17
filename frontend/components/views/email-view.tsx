import { useDraftState } from '@/hooks/use-draft-state';
import { getSession } from 'next-auth/react';
import React, { useEffect, useState } from 'react';
import gatewayClient from '../../lib/gateway-client';
import { getProvider } from '../../lib/session-utils';
import EmailFilters from '../email/email-filters';
import EmailThread from '../email/email-thread';

const OpenDraftPaneButton: React.FC = () => {
    const { createNewDraft } = useDraftState();
    const handleClick = async () => {
        const session = await getSession();
        const userId = session?.user?.id || 'anonymous';
        createNewDraft('email', userId);
        // Optionally, scroll to or focus the draft pane if needed
    };
    return (
        <button className="btn btn-primary" onClick={handleClick}>
            Compose Email
        </button>
    );
};

const EmailView: React.FC = () => {
    const [threads, setThreads] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [filters, setFilters] = useState({});

    useEffect(() => {
        let isMounted = true;
        setLoading(true);
        (async () => {
            try {
                const session = await getSession();
                const provider = getProvider(session);
                if (!provider) throw new Error('No provider found in session');
                // TODO: support pagination, filtering, etc.
                const emailsResp: any = await gatewayClient.getEmails(provider, 50, 0);
                // Assume emailsResp is an array of emails, group by thread/conversation
                // For now, treat as flat list, group logic can be added later
                if (isMounted) setThreads(emailsResp.threads || emailsResp || []);
                setError(null);
            } catch (e: any) {
                if (isMounted) setError(e.message || 'Failed to load emails');
            } finally {
                if (isMounted) setLoading(false);
            }
        })();
        return () => { isMounted = false; };
    }, [filters]);

    return (
        <div className="flex flex-col h-full">
            <div className="p-4 border-b">
                <div className="flex items-center justify-between">
                    <h1 className="text-xl font-semibold">Inbox</h1>
                    <OpenDraftPaneButton />
                </div>
                <EmailFilters filters={filters} setFilters={setFilters} />
            </div>
            <div className="flex-1 overflow-y-auto">
                {loading ? (
                    <div className="p-8 text-center text-muted-foreground">Loading…</div>
                ) : error ? (
                    <div className="p-8 text-center text-red-500">{error}</div>
                ) : threads.length === 0 ? (
                    <div className="p-8 text-center text-muted-foreground">No emails found.</div>
                ) : (
                    threads.map((thread: any) => (
                        <EmailThread key={thread.id || thread[0]?.id} thread={thread} />
                    ))
                )}
            </div>
        </div>
    );
};

export default EmailView; 