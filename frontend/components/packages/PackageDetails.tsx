import { useEffect, useState } from 'react';
import { gatewayClient } from '../../lib/gateway-client';
import type { Package, TrackingEvent } from './AddPackageModal';
import LabelChip from './LabelChip';
import TrackingTimeline from './TrackingTimeline';

export default function PackageDetails({ pkg, onClose }: { pkg: Package & { labels?: (string | { name: string })[], events?: TrackingEvent[] }, onClose: () => void }) {
    const [events, setEvents] = useState<TrackingEvent[]>([]);
    const [loadingEvents, setLoadingEvents] = useState(false);
    const [eventsError, setEventsError] = useState<string | null>(null);

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                onClose();
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [onClose]);

    // Fetch events when modal opens
    useEffect(() => {
        const fetchEvents = async () => {
            if (!pkg.id) return;

            setLoadingEvents(true);
            setEventsError(null);
            try {
                const fetchedEvents = await gatewayClient.getTrackingEvents(pkg.id);
                setEvents(fetchedEvents);
            } catch (error) {
                console.error('Failed to fetch tracking events:', error);
                setEventsError('Failed to load tracking events');
            } finally {
                setLoadingEvents(false);
            }
        };

        fetchEvents();
    }, [pkg.id]);

    return (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-lg max-w-lg w-full max-h-[90vh] flex flex-col">
                <div className="p-6 pb-4 border-b border-gray-200">
                    <button
                        className="absolute top-2 right-2 text-gray-400 hover:text-gray-600 text-3xl font-bold p-2 leading-none focus:outline-none"
                        onClick={onClose}
                        aria-label="Close"
                    >
                        &times;
                    </button>
                    <h2 className="text-xl font-bold mb-2">Package Details</h2>
                </div>
                <div className="flex-1 overflow-y-auto p-6 pt-4">
                    <div className="space-y-3">
                        <div><b>Tracking Number:</b> {pkg.tracking_number}</div>
                        <div><b>Carrier:</b> {pkg.carrier}</div>
                        <div><b>Status:</b> {pkg.status}</div>
                        <div><b>Estimated Delivery:</b> {pkg.estimated_delivery}</div>
                        <div><b>Recipient:</b> {pkg.recipient_name}</div>
                        <div><b>Description:</b> {pkg.package_description}</div>
                        <div><b>Labels:</b> {(pkg.labels || []).map((label: string | { name: string }, idx: number) => <LabelChip key={idx} label={typeof label === 'string' ? label : label?.name || ''} />)}</div>
                        <div><b>Order Number:</b> {pkg.order_number}</div>
                        <div><b>Tracking Link:</b> <a href={pkg.tracking_link} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">View</a></div>
                        <div><b>Events:</b></div>
                        {loadingEvents ? (
                            <div className="text-sm text-gray-500">Loading events...</div>
                        ) : eventsError ? (
                            <div className="text-sm text-red-500">{eventsError}</div>
                        ) : events.length === 0 ? (
                            <div className="text-sm text-gray-500">No tracking events found.</div>
                        ) : (
                            <TrackingTimeline events={events} />
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
