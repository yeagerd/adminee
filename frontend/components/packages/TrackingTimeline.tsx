import { Loader2, Trash2 } from 'lucide-react';
import { Button } from '../ui/button';

interface TrackingEvent {
    id?: string;
    event_date: string;
    status: string;
    location?: string;
    description?: string;
}

interface TrackingTimelineProps {
    events: TrackingEvent[];
    onDeleteEvent?: (eventId: string) => Promise<void>;
    deletingEventId?: string | null;
}

export default function TrackingTimeline({ events, onDeleteEvent, deletingEventId }: TrackingTimelineProps) {
    return (
        <ol className="border-l-2 border-blue-500 pl-4">
            {events.map((event, idx) => (
                <li key={idx} className="mb-4">
                    <div className="flex items-start justify-between">
                        <div className="flex-1">
                            <div className="text-xs text-gray-400">{new Date(event.event_date).toLocaleString()}</div>
                            <div className="font-semibold">{event.status}</div>
                            {event.location && <div className="text-sm text-gray-500">{event.location}</div>}
                            {event.description && <div className="text-xs text-gray-400">{event.description}</div>}
                        </div>
                        {onDeleteEvent && event.id && (
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => onDeleteEvent(event.id!)}
                                disabled={deletingEventId === event.id}
                                className="ml-2 h-8 w-8 p-0 text-gray-400 hover:text-red-500 hover:bg-red-50 disabled:opacity-50"
                                aria-label="Delete tracking event"
                            >
                                {deletingEventId === event.id ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                    <Trash2 className="h-4 w-4" />
                                )}
                            </Button>
                        )}
                    </div>
                </li>
            ))}
        </ol>
    );
}
