import { useEffect } from 'react';
import type { Package, TrackingEvent } from './AddPackageModal';
import LabelChip from './LabelChip';
import TrackingTimeline from './TrackingTimeline';

export default function PackageDetails({ pkg, onClose }: { pkg: Package & { labels?: (string | { name: string })[], events?: TrackingEvent[] }, onClose: () => void }) {
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                onClose();
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [onClose]);
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
                        <TrackingTimeline events={pkg.events || []} />
                    </div>
                </div>
            </div>
        </div>
    );
}
