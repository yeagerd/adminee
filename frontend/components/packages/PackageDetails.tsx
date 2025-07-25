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
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-lg max-w-lg w-full p-6 relative">
                <button
                    className="absolute top-2 right-2 text-gray-400 hover:text-gray-600 text-3xl font-bold p-2 leading-none focus:outline-none"
                    onClick={onClose}
                    aria-label="Close"
                >
                    &times;
                </button>
                <h2 className="text-xl font-bold mb-2">Package Details</h2>
                <div className="mb-2"><b>Tracking Number:</b> {pkg.tracking_number}</div>
                <div className="mb-2"><b>Carrier:</b> {pkg.carrier}</div>
                <div className="mb-2"><b>Status:</b> {pkg.status}</div>
                <div className="mb-2"><b>Estimated Delivery:</b> {pkg.estimated_delivery}</div>
                <div className="mb-2"><b>Recipient:</b> {pkg.recipient_name}</div>
                <div className="mb-2"><b>Description:</b> {pkg.package_description}</div>
                <div className="mb-2"><b>Labels:</b> {(pkg.labels || []).map((label: string | { name: string }, idx: number) => <LabelChip key={idx} label={typeof label === 'string' ? label : label?.name || ''} />)}</div>
                <div className="mb-2"><b>Order Number:</b> {pkg.order_number}</div>
                <div className="mb-2"><b>Tracking Link:</b> <a href={pkg.tracking_link} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">View</a></div>
                <div className="mb-2"><b>Events:</b></div>
                <TrackingTimeline events={pkg.events || []} />
            </div>
        </div>
    );
}
