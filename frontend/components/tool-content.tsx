'use client';

import DraftsList from '@/components/drafts/drafts-list';
import { MeetingPollEdit } from '@/components/meetings/meeting-poll-edit';
import { MeetingPollNew } from '@/components/meetings/meeting-poll-new';
import { MeetingPollResults } from '@/components/meetings/meeting-poll-results';
import PackageDashboard from '@/components/packages/PackageDashboard';
import { Button } from '@/components/ui/button';
import { useIntegrations } from '@/contexts/integrations-context';
import { useToolStateUtils } from '@/hooks/use-tool-state';
import { meetingsApi } from '@/api';
import { MeetingSubView } from '@/types/navigation';
import { useSession } from 'next-auth/react';
import { useEffect, useState } from 'react';
import CalendarView from './views/calendar-view';
import EmailView from './views/email-view';
import ContactsView from './views/contacts-view';

// Define MeetingPoll type for frontend use
export interface MeetingPoll {
    id: string;
    title: string;
    status: string;
    created_at: string;
    updated_at: string;
    poll_token: string;
    // Add other fields as needed from backend schema
}

export function ToolContent() {
    const {
        activeTool,
        setMeetingSubView,
        getMeetingSubView,
        getMeetingPollId
    } = useToolStateUtils();
    const { data: session } = useSession();
    const { loading: integrationsLoading, triggerAutoRefreshIfNeeded } = useIntegrations();

    // Call auto-refresh logic on every tool change
    useEffect(() => {
        triggerAutoRefreshIfNeeded().catch(error => {
            console.error('Failed to trigger auto-refresh:', error);
        });
    }, [activeTool, triggerAutoRefreshIfNeeded]);

    // Compute a loading boolean for tool data readiness
    const toolDataLoading = integrationsLoading || !session?.user?.id;

    // Meetings dashboard state and logic
    const [polls, setPolls] = useState<MeetingPoll[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchPolls = () => {
        setLoading(true);
        meetingsApi.listMeetingPolls()
            .then((data) => setPolls(data as MeetingPoll[]))
            .catch((e: unknown) => {
                if (e && typeof e === 'object' && 'message' in e) {
                    setError((e as { message?: string }).message || 'Failed to load polls');
                } else {
                    setError('Failed to load polls');
                }
            })
            .finally(() => setLoading(false));
    };

    // Track meeting sub-view state to avoid duplicate API calls
    const [localMeetingSubView, setLocalMeetingSubView] = useState<MeetingSubView>('list');

    useEffect(() => {
        // Update local state when meeting sub-view changes
        setLocalMeetingSubView(getMeetingSubView());
    }, [getMeetingSubView]);

    useEffect(() => {
        if (activeTool === 'meetings') {
            fetchPolls();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeTool, localMeetingSubView]);


    const renderToolContent = () => {
        switch (activeTool) {
            case 'calendar':
                return <CalendarView toolDataLoading={toolDataLoading} activeTool={activeTool} />;
            case 'email':
                return <EmailView toolDataLoading={toolDataLoading} activeTool={activeTool} />;
            case 'contacts':
                return <ContactsView toolDataLoading={toolDataLoading} activeTool={activeTool} />;
            case 'documents':
                return (
                    <div className="p-8">
                        <h1 className="text-3xl font-bold mb-4">Documents</h1>
                        <p>Documents view coming soon...</p>
                    </div>
                );
            case 'tasks':
                return (
                    <div className="p-8">
                        <h1 className="text-3xl font-bold mb-4">Tasks</h1>
                        <p>Tasks view coming soon...</p>
                    </div>
                );
            case 'packages':
                return <PackageDashboard />;
            case 'research':
                return (
                    <div className="p-8">
                        <h1 className="text-3xl font-bold mb-4">Research</h1>
                        <p>Research view coming soon...</p>
                    </div>
                );
            case 'pulse':
                return (
                    <div className="p-8">
                        <h1 className="text-3xl font-bold mb-4">Pulse</h1>
                        <p>Pulse view coming soon...</p>
                    </div>
                );
            case 'insights':
                return (
                    <div className="p-8">
                        <h1 className="text-3xl font-bold mb-4">Insights</h1>
                        <p>Insights view coming soon...</p>
                    </div>
                );
            case 'drafts':
                return (
                    <div className="p-8">
                        <h1 className="text-3xl font-bold mb-4">Drafts</h1>
                        <DraftsList />
                    </div>
                );
            case 'meetings':
                const meetingSubView = getMeetingSubView();
                const meetingPollId = getMeetingPollId();

                // Handle different meeting sub-views
                switch (meetingSubView) {
                    case 'view':
                        if (!meetingPollId) {
                            setMeetingSubView('list');
                            return null;
                        }
                        return <MeetingPollResults pollId={meetingPollId} />;

                    case 'edit':
                        if (!meetingPollId) {
                            setMeetingSubView('list');
                            return null;
                        }
                        return <MeetingPollEdit pollId={meetingPollId} />;

                    case 'new':
                        return <MeetingPollNew />;

                    case 'list':
                    default:
                        return (
                            <div className="p-8">
                                <div className="flex items-center justify-between mb-6">
                                    <h1 className="text-2xl font-bold">Meeting Polls</h1>
                                    <Button
                                        onClick={() => {
                                            // Navigate into new poll flow and seed URL with view=new&step=1
                                            const url = new URL(window.location.href);
                                            url.searchParams.set('view', 'new');
                                            url.searchParams.set('step', '1');
                                            window.history.pushState({ step: 1 }, '', url.toString());
                                            setMeetingSubView('new');
                                        }}
                                        className="bg-teal-600 text-white px-4 py-2 rounded shadow hover:bg-teal-700 font-semibold"
                                    >
                                        + New Meeting Poll
                                    </Button>
                                </div>
                                {loading ? (
                                    <div>Loading...</div>
                                ) : error ? (
                                    <div className="text-red-600">{error}</div>
                                ) : polls.length === 0 ? (
                                    <div className="text-gray-500">No meeting polls found.</div>
                                ) : (
                                    <table className="min-w-full bg-white border rounded shadow">
                                        <thead>
                                            <tr>
                                                <th className="px-4 py-2 border-b">Title</th>
                                                <th className="px-4 py-2 border-b">Status</th>
                                                <th className="px-4 py-2 border-b">Created</th>
                                                <th className="px-4 py-2 border-b">Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {polls.map((poll) => (
                                                <tr key={poll.id} className="hover:bg-gray-50">
                                                    <td className="px-4 py-2 border-b font-medium">{poll.title}</td>
                                                    <td className="px-4 py-2 border-b capitalize">{poll.status}</td>
                                                    <td className="px-4 py-2 border-b whitespace-nowrap">{poll.created_at?.slice(0, 10) || ""}</td>
                                                    <td className="px-4 py-2 border-b space-x-2">
                                                        <button
                                                            onClick={() => setMeetingSubView('view', poll.id)}
                                                            className="text-teal-600 hover:underline font-semibold"
                                                        >
                                                            View
                                                        </button>
                                                        <button
                                                            onClick={() => setMeetingSubView('edit', poll.id)}
                                                            className="text-blue-600 hover:underline font-semibold"
                                                        >
                                                            Edit
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                )}
                            </div>
                        );
                }
            default:
                return (
                    <div className="p-8">
                        <h1 className="text-3xl font-bold mb-4">Dashboard</h1>
                        <p>Welcome back, {session?.user?.name || 'User'}!</p>
                    </div>
                );
        }
    };

    return (
        <div className="h-full flex flex-col">
            {/* Tool Content - Top portion */}
            <div className="flex-1 overflow-auto">
                {renderToolContent()}
            </div>
        </div>
    );
} 