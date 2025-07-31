import { safeParseDateToLocaleString } from '@/lib/utils';

export default function TrackingTimeline({ events }: { events: { event_date: string, status: string, location?: string, description?: string }[] }) {
    return (
        <ol className="border-l-2 border-blue-500 pl-4">
            {events.map((event, idx) => (
                <li key={idx} className="mb-4">
                    <div className="text-xs text-gray-400">{safeParseDateToLocaleString(event.event_date, {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                    })}</div>
                    <div className="font-semibold">{event.status}</div>
                    {event.location && <div className="text-sm text-gray-500">{event.location}</div>}
                    {event.description && <div className="text-xs text-gray-400">{event.description}</div>}
                </li>
            ))}
        </ol>
    );
}
