import { Button } from '@/components/ui/button';
import { Trash2 } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { gatewayClient } from '../../lib/gateway-client';
import type { Package, TrackingEvent } from './AddPackageModal';
import LabelChip from './LabelChip';
import TrackingTimeline from './TrackingTimeline';

export default function PackageDetails({
    pkg,
    onClose,
    onRefresh
}: {
    pkg: Package & { labels?: (string | { name: string })[], events?: TrackingEvent[] },
    onClose: () => void,
    onRefresh?: () => void
}) {
    const [events, setEvents] = useState<TrackingEvent[]>([]);
    const [loadingEvents, setLoadingEvents] = useState(false);
    const [eventsError, setEventsError] = useState<string | null>(null);
    const [deletingEventId, setDeletingEventId] = useState<string | null>(null);
    const [showDeleteDialog, setShowDeleteDialog] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    const modalRef = useRef<HTMLDivElement>(null);
    const mountedRef = useRef(true);

    useEffect(() => {
        return () => {
            mountedRef.current = false;
        };
    }, []);

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                onClose();
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [onClose]);

    // Handle click outside to close
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (modalRef.current && !modalRef.current.contains(event.target as Node)) {
                // TODO: In the future, check for unsaved changes here before closing
                // For now, close immediately
                onClose();
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
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

    const handleDeleteEvent = async (eventId: string) => {
        if (!confirm('Are you sure you want to delete this tracking event? This action cannot be undone.')) {
            return;
        }

        setDeletingEventId(eventId);
        try {
            await gatewayClient.deleteTrackingEvent(pkg.id!, eventId);
            // Remove the deleted event from the local state
            setEvents(prevEvents => prevEvents.filter(event => event.id !== eventId));
        } catch (error) {
            console.error('Failed to delete tracking event:', error);
            alert('Failed to delete tracking event. Please try again.');
        } finally {
            setDeletingEventId(null);
        }
    };

    const handleDeletePackage = async () => {
        if (!pkg.id) {
            return;
        }

        setIsDeleting(true);
        try {
            await gatewayClient.deletePackage(pkg.id);
            // Close the modal after successful deletion
            onClose();
            onRefresh?.(); // Call onRefresh if provided
        } catch (error) {
            console.error('Failed to delete package:', error);
            alert('Failed to delete package. Please try again.');
        } finally {
            // Only update state if component is still mounted
            if (mountedRef.current) {
                setIsDeleting(false);
                setShowDeleteDialog(false); // Close the confirmation dialog
            }
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 p-4">
            <div ref={modalRef} className="bg-white rounded-lg shadow-lg max-w-lg w-full max-h-[90vh] flex flex-col relative">
                {/* Header */}
                <div className="p-6 pb-4 border-b border-gray-200 flex-shrink-0">
                    <div className="flex items-center justify-between">
                        <h2 className="text-xl font-bold">Package Details</h2>
                        <button
                            className="text-gray-400 hover:text-gray-600 text-2xl font-bold w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-300"
                            onClick={onClose}
                            aria-label="Close"
                        >
                            &times;
                        </button>
                    </div>
                </div>

                {/* Scrollable Content */}
                <div className="flex-1 overflow-y-auto p-6">
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
                            <TrackingTimeline
                                events={events}
                                onDeleteEvent={handleDeleteEvent}
                                deletingEventId={deletingEventId}
                            />
                        )}
                    </div>
                </div>

                {/* Footer with Delete Button */}
                <div className="p-6 pt-4 border-t border-gray-200 flex-shrink-0">
                    <Button
                        variant="destructive"
                        className="w-full flex items-center justify-center gap-2"
                        onClick={() => {
                            setShowDeleteDialog(true);
                        }}
                    >
                        <Trash2 className="h-4 w-4" />
                        Delete Package
                    </Button>
                </div>

                {/* Simple Confirmation Modal */}
                {showDeleteDialog && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60]">
                        <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
                            <h3 className="text-lg font-semibold mb-2">Delete Package?</h3>
                            <p className="text-sm text-gray-600 mb-6">
                                This action cannot be undone. This will permanently delete the package and all its associated tracking events.
                            </p>
                            <div className="flex gap-3 justify-end">
                                <Button
                                    variant="outline"
                                    onClick={() => {
                                        setShowDeleteDialog(false);
                                    }}
                                >
                                    Cancel
                                </Button>
                                <Button
                                    variant="destructive"
                                    onClick={() => {
                                        handleDeletePackage();
                                    }}
                                    disabled={isDeleting}
                                >
                                    {isDeleting ? 'Deleting...' : 'Delete Package'}
                                </Button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
