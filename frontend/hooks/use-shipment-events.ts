import { shipmentsApi } from '@/api';
import { useEffect, useState } from 'react';

export interface ShipmentEvent {
    id: string;
    event_date: string;
    status: string;
    location?: string;
    description?: string;
    created_at: string;
}

export const useShipmentEvents = (emailId: string) => {
    const [events, setEvents] = useState<ShipmentEvent[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!emailId) {
            setEvents([]);
            return;
        }

        const fetchEvents = async () => {
            setLoading(true);
            setError(null);

            try {
                const response = await shipmentsApi.getEventsByEmail(emailId);
                setEvents(response.map(event => ({
                    id: event.id,
                    event_date: event.event_date,
                    status: event.status,
                    location: event.location || undefined,
                    description: event.description || undefined,
                    created_at: event.created_at
                })));
            } catch (err) {
                const errorMessage = err instanceof Error ? err.message : 'Failed to fetch shipment events';
                setError(errorMessage);
                console.error('Error fetching shipment events:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchEvents();
    }, [emailId]);

    return {
        data: events,
        isLoading: loading,
        error,
        hasEvents: events.length > 0
    };
}; 