'use client';

import { CalendarEventItem } from '@/components/calendar-event-item';
import DraftsList from '@/components/drafts/drafts-list';
import { MeetingPollEdit } from '@/components/meetings/meeting-poll-edit';
import { MeetingPollNew } from '@/components/meetings/meeting-poll-new';
import { MeetingPollResults } from '@/components/meetings/meeting-poll-results';
import PackageDashboard from '@/components/packages/PackageDashboard';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useIntegrations } from '@/contexts/integrations-context';
import { useUserPreferences } from '@/contexts/settings-context';
import { useToolStateUtils } from '@/hooks/use-tool-state';
import { gatewayClient } from '@/lib/gateway-client';
import { CalendarEvent } from '@/types/office-service';
import { AlertCircle, ExternalLink } from 'lucide-react';
import { useSession } from 'next-auth/react';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import EmailView from './views/email-view';

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
    const { effectiveTimezone } = useUserPreferences();
    const [calendarEvents, setCalendarEvents] = useState<CalendarEvent[]>([]);
    const [calendarLoading, setCalendarLoading] = useState(false);
    const [calendarError, setCalendarError] = useState<string | null>(null);
    const { loading: integrationsLoading, activeProviders, triggerAutoRefreshIfNeeded } = useIntegrations();

    // Call auto-refresh logic on every tool change
    useEffect(() => {
        triggerAutoRefreshIfNeeded();
    }, [activeTool, triggerAutoRefreshIfNeeded]);

    // Compute a loading boolean for tool data readiness
    const toolDataLoading = integrationsLoading || !session?.user?.id;

    const fetchCalendarEvents = useCallback(async () => {
        if (!session?.user?.id) {
            setCalendarError('No user session');
            return;
        }
        if (!activeProviders || activeProviders.length === 0) {
            setCalendarError('No active calendar integrations found');
            setCalendarEvents([]);
            return;
        }
        setCalendarLoading(true);
        setCalendarError(null);
        try {
            const response = await gatewayClient.getCalendarEvents(
                activeProviders,
                10,
                new Date().toISOString().split('T')[0],
                new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
                undefined,
                undefined,
                effectiveTimezone // Pass the effective timezone
            );
            if (response.success && response.data) {
                setCalendarEvents(response.data.events || []);
            } else {
                setCalendarError('Failed to fetch calendar events');
            }
        } catch (err) {
            console.error('Calendar fetch error:', err);
            setCalendarError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setCalendarLoading(false);
        }
    }, [session?.user?.id, activeProviders, effectiveTimezone]);

    // Fetch calendar events when integrations are loaded and user has active calendar integrations
    useEffect(() => {
        if (activeTool === 'calendar' && !integrationsLoading && session?.user?.id && activeProviders.length > 0) {
            fetchCalendarEvents();
        }
    }, [activeTool, integrationsLoading, activeProviders, session?.user?.id, fetchCalendarEvents, effectiveTimezone]);

    // Use activeProviders to check for active calendar integrations
    const hasActiveCalendarIntegration = activeProviders.length > 0;

    // Meetings dashboard state and logic
    const [polls, setPolls] = useState<MeetingPoll[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchPolls = () => {
        setLoading(true);
        gatewayClient.listMeetingPolls()
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

    useEffect(() => {
        if (activeTool === 'meetings') {
            fetchPolls();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeTool]);



    const renderToolContent = () => {
        switch (activeTool) {
            case 'calendar':
                return (
                    <div className="p-8">
                        <div className="flex items-center justify-between mb-6">
                            <h1 className="text-3xl font-bold">Calendar</h1>
                            <Button onClick={fetchCalendarEvents} disabled={calendarLoading}>
                                {calendarLoading ? 'Loading...' : 'Refresh'}
                            </Button>
                        </div>

                        {/* Integration Status Warning */}
                        {!integrationsLoading && !hasActiveCalendarIntegration && (
                            <Alert className="mb-6 border-amber-200 bg-amber-50">
                                <AlertCircle className="h-4 w-4 text-amber-600" />
                                <AlertDescription className="text-amber-800">
                                    <div className="flex items-center justify-between">
                                        <span>
                                            No active calendar integration found. Connect your Google Calendar or Microsoft Outlook to view your events.
                                        </span>
                                        <Link
                                            href="/settings?page=integrations"
                                            className="inline-flex items-center gap-1 text-amber-700 hover:text-amber-900 font-medium"
                                        >
                                            <span>Go to Integrations</span>
                                            <ExternalLink className="h-3 w-3" />
                                        </Link>
                                    </div>
                                </AlertDescription>
                            </Alert>
                        )}

                        {calendarError && (
                            <Card className="mb-6">
                                <CardContent className="pt-6">
                                    <div className="p-3 bg-red-100 border border-red-300 rounded text-red-700">
                                        Error: {calendarError}
                                    </div>
                                </CardContent>
                            </Card>
                        )}

                        {calendarLoading && (
                            <Card>
                                <CardContent className="pt-6">
                                    <div className="flex items-center justify-center py-8">
                                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></div>
                                        <span className="ml-3">Loading calendar events...</span>
                                    </div>
                                </CardContent>
                            </Card>
                        )}

                        {!calendarLoading && calendarEvents.length === 0 && !calendarError && hasActiveCalendarIntegration && (
                            <Card>
                                <CardContent className="pt-6">
                                    <div className="text-center py-8 text-muted-foreground">
                                        <p>No calendar events found for the next 7 days.</p>
                                        <Button
                                            variant="outline"
                                            className="mt-4"
                                            onClick={fetchCalendarEvents}
                                        >
                                            Try Again
                                        </Button>
                                    </div>
                                </CardContent>
                            </Card>
                        )}

                        {!calendarLoading && calendarEvents.length > 0 && (
                            <div className="space-y-4">
                                <div className="text-sm text-muted-foreground">
                                    Found {calendarEvents.length} events for the next 7 days
                                </div>
                                {calendarEvents.map((event) => (
                                    <CalendarEventItem key={event.id} event={event} effectiveTimezone={effectiveTimezone} />
                                ))}
                            </div>
                        )}
                    </div>
                );
            case 'email':
                return <EmailView toolDataLoading={toolDataLoading} activeTool={activeTool} />;
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
                                        onClick={() => setMeetingSubView('new')}
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