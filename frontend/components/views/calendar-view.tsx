import { useIntegrations } from '@/contexts/integrations-context';
import { useUserPreferences } from '@/contexts/settings-context';
import { officeApi } from '@/api';
import type { CalendarEvent } from '@/types/api/office';
import { getSession } from 'next-auth/react';
import React, { useCallback, useEffect, useState } from 'react';
import CalendarGridView from './calendar-grid-view';

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

            const response = await officeApi.getCalendarEvents(
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



    return (
        <div className="h-full flex flex-col">
            {/* Content */}
            <div className="flex-1 overflow-hidden">
                <CalendarGridView
                    toolDataLoading={toolDataLoading}
                    activeTool={activeTool}
                    events={events}
                    loading={loading}
                    refreshing={refreshing}
                    error={error}
                    onRefresh={handleRefresh}
                />
            </div>
        </div>
    );
};

export default CalendarView; 