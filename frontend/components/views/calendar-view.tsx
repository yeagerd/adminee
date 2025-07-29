import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useIntegrations } from '@/contexts/integrations-context';
import { useUserPreferences } from '@/contexts/settings-context';
import { gatewayClient } from '@/lib/gateway-client';
import type { CalendarEvent } from '@/types/office-service';
import { AlertCircle, ExternalLink, RefreshCw } from 'lucide-react';
import { getSession } from 'next-auth/react';
import Link from 'next/link';
import React, { useCallback, useEffect, useState } from 'react';
import { CalendarEventItem } from '../calendar-event-item';

interface CalendarViewProps {
    toolDataLoading?: boolean;
    activeTool?: string;
}

const CalendarView: React.FC<CalendarViewProps> = ({ toolDataLoading = false, activeTool }) => {
    const [events, setEvents] = useState<CalendarEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const { loading: integrationsLoading, activeProviders } = useIntegrations();
    const { effectiveTimezone } = useUserPreferences();

    const fetchCalendarEvents = useCallback(async (noCache = false) => {
        if (!activeProviders || activeProviders.length === 0) {
            return;
        }

        try {
            const session = await getSession();
            const userId = session?.user?.id;
            if (!userId) throw new Error('No user id found in session');

            const response = await gatewayClient.getCalendarEvents(
                activeProviders,
                10,
                new Date().toISOString().split('T')[0],
                new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
                undefined,
                undefined,
                effectiveTimezone,
                noCache
            );

            if (response.success && response.data) {
                const events = Array.isArray(response.data) ? response.data : [];
                setEvents(events);
                setError(null);
            } else {
                setError('Failed to fetch calendar events');
            }
        } catch (e: unknown) {
            setError((e && typeof e === 'object' && 'message' in e) ? (e as { message?: string }).message || 'Failed to load calendar events' : 'Failed to load calendar events');
        }
    }, [activeProviders, effectiveTimezone]);

    const handleRefresh = useCallback(async () => {
        setRefreshing(true);
        try {
            await fetchCalendarEvents(true); // Pass true to bypass cache
        } finally {
            setRefreshing(false);
        }
    }, [fetchCalendarEvents]);

    useEffect(() => {
        // Only fetch when the tab is actually activated
        if (toolDataLoading) return;
        if (integrationsLoading) return;
        if ((!activeProviders || activeProviders.length === 0)) {
            setError('No active calendar integrations found. Please connect your calendar account first.');
            setEvents([]);
            setLoading(false);
            return;
        }
        if (activeTool !== 'calendar') {
            setLoading(false);
            return;
        }

        let isMounted = true;
        setLoading(true);
        (async () => {
            try {
                await fetchCalendarEvents(false); // Use cached data for initial load
            } finally {
                if (isMounted) setLoading(false);
            }
        })();
        return () => { isMounted = false; };
    }, [activeProviders, integrationsLoading, toolDataLoading, activeTool, fetchCalendarEvents]);

    // Use activeProviders to check for active calendar integrations
    const hasActiveCalendarIntegration = activeProviders.length > 0;

    return (
        <div className="p-8">
            <div className="flex items-center justify-between mb-6">
                <h1 className="text-3xl font-bold">Calendar</h1>
                <div className="flex items-center gap-2">
                    <button
                        onClick={handleRefresh}
                        disabled={refreshing || loading}
                        className="p-2 text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
                        title="Refresh calendar events"
                    >
                        <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                    </button>
                </div>
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

            {error && (
                <Card className="mb-6">
                    <CardContent className="pt-6">
                        <div className="p-3 bg-red-100 border border-red-300 rounded text-red-700">
                            Error: {error}
                        </div>
                    </CardContent>
                </Card>
            )}

            {loading && (
                <Card>
                    <CardContent className="pt-6">
                        <div className="flex items-center justify-center py-8">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></div>
                            <span className="ml-3">Loading calendar events...</span>
                        </div>
                    </CardContent>
                </Card>
            )}

            {!loading && events.length === 0 && !error && hasActiveCalendarIntegration && (
                <Card>
                    <CardContent className="pt-6">
                        <div className="text-center py-8 text-muted-foreground">
                            <p>No calendar events found for the next 7 days.</p>
                            <Button
                                variant="outline"
                                className="mt-4"
                                onClick={() => fetchCalendarEvents(false)}
                            >
                                Try Again
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            )}

            {!loading && events.length > 0 && (
                <div className="space-y-4">
                    <div className="text-sm text-muted-foreground">
                        Found {events.length} events for the next 7 days
                    </div>
                    {events.map((event) => (
                        <CalendarEventItem key={event.id} event={event} effectiveTimezone={effectiveTimezone} />
                    ))}
                </div>
            )}
        </div>
    );
};

export default CalendarView; 