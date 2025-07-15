'use client';

import { CalendarEventItem } from '@/components/calendar-event-item';
import DraftsList from '@/components/drafts/drafts-list';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useToolStateUtils } from '@/hooks/use-tool-state';
import { INTEGRATION_STATUS } from '@/lib/constants';
import { gatewayClient, Integration } from '@/lib/gateway-client';
import { CalendarEvent } from '@/types/office-service';
import { AlertCircle, ExternalLink } from 'lucide-react';
import { useSession } from 'next-auth/react';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';

export function ToolContent() {
    const { activeTool } = useToolStateUtils();
    const { data: session } = useSession();
    const [calendarEvents, setCalendarEvents] = useState<CalendarEvent[]>([]);
    const [calendarLoading, setCalendarLoading] = useState(false);
    const [calendarError, setCalendarError] = useState<string | null>(null);
    const [integrations, setIntegrations] = useState<Integration[]>([]);
    const [integrationsLoading, setIntegrationsLoading] = useState(false);

    const fetchIntegrations = useCallback(async () => {
        if (!session?.user?.id) return;

        setIntegrationsLoading(true);
        try {
            const response = await gatewayClient.getIntegrations();
            setIntegrations(response.integrations || []);
        } catch (err) {
            console.error('Failed to fetch integrations:', err);
        } finally {
            setIntegrationsLoading(false);
        }
    }, [session?.user?.id]);

    const fetchCalendarEvents = useCallback(async () => {
        if (!session?.user?.id) {
            setCalendarError('No user session');
            return;
        }

        setCalendarLoading(true);
        setCalendarError(null);

        try {
            const response = await gatewayClient.getCalendarEvents(
                session.user.id,
                session.provider ? [session.provider] : ['google', 'microsoft'],
                10,
                new Date().toISOString().split('T')[0],
                new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
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
    }, [session?.user?.id, session?.provider]);

    // Fetch integrations and calendar events when calendar tool is selected
    useEffect(() => {
        if (activeTool === 'calendar' && session?.user?.id) {
            fetchIntegrations();
            fetchCalendarEvents();
        }
    }, [activeTool, session?.user?.id, fetchIntegrations, fetchCalendarEvents]);

    // Check if user has active calendar integrations
    const hasActiveCalendarIntegration = integrations.some(
        integration =>
            integration.status === INTEGRATION_STATUS.ACTIVE &&
            (integration.provider === 'google' || integration.provider === 'microsoft')
    );

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
                                            href="/integrations"
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
                                    <CalendarEventItem key={event.id} event={event} />
                                ))}
                            </div>
                        )}
                    </div>
                );
            case 'email':
                return (
                    <div className="p-8">
                        <h1 className="text-3xl font-bold mb-4">Email</h1>
                        <p>Email view coming soon...</p>
                    </div>
                );
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
                return (
                    <div className="p-8">
                        <h1 className="text-3xl font-bold mb-4">Package Tracker</h1>
                        <p>Package tracker view coming soon...</p>
                    </div>
                );
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