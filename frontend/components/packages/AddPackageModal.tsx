import { gatewayClient } from '@/lib/gateway-client';
import { useState } from 'react';

export interface TrackingEvent {
    event_date: string;
    status: string;
    location?: string;
    description?: string;
}

export interface Package {
    id?: number;
    tracking_number: string;
    carrier: string;
    status: string;
    estimated_delivery?: string;
    actual_delivery?: string;
    recipient_name?: string;
    recipient_address?: string;
    shipper_name?: string;
    package_description?: string;
    order_number?: string;
    tracking_link?: string;
    email_message_id?: string;
    labels?: (string | { name: string })[];
    events?: TrackingEvent[];
    [key: string]: unknown;
}

const initialState: Package = {
    tracking_number: '',
    carrier: '',
    status: 'pending',
    estimated_delivery: '',
    actual_delivery: '',
    recipient_name: '',
    recipient_address: '',
    shipper_name: '',
    package_description: '',
    order_number: '',
    tracking_link: '',
    email_message_id: '',
};

const STATUS_OPTIONS = [
    { value: 'pending', label: 'Pending' },
    { value: 'in_transit', label: 'In Transit' },
    { value: 'out_for_delivery', label: 'Out for Delivery' },
    { value: 'delivered', label: 'Delivered' },
    { value: 'delayed', label: 'Delayed' },
    { value: 'exception', label: 'Exception' },
    { value: 'cancelled', label: 'Cancelled' },
];

export default function AddPackageModal({ onClose, onAdd }: { onClose: () => void, onAdd: () => void }) {
    const [form, setForm] = useState(initialState);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
        const { name, value } = e.target;
        setForm((prev) => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        try {
            await gatewayClient.request('/api/packages', {
                method: 'POST',
                body: {
                    tracking_number: form.tracking_number,
                    carrier: form.carrier,
                    status: form.status,
                    estimated_delivery: form.estimated_delivery || null,
                    actual_delivery: form.actual_delivery || null,
                    recipient_name: form.recipient_name || null,
                    recipient_address: form.recipient_address || null,
                    shipper_name: form.shipper_name || null,
                    package_description: form.package_description || null,
                    order_number: form.order_number || null,
                    tracking_link: form.tracking_link || null,
                    email_message_id: form.email_message_id || null,
                },
            });
            onAdd();
        } catch (err: unknown) {
            if (err instanceof Error) {
                setError(err.message);
            } else if (typeof err === 'object' && err !== null && 'message' in err) {
                setError(String((err as { message: string }).message));
            } else {
                setError('Unknown error');
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50">
            <div className="bg-white rounded shadow-lg p-8 w-full max-w-md">
                <h2 className="text-lg font-bold mb-4">Add Package</h2>
                <form onSubmit={handleSubmit} className="space-y-3">
                    <input name="tracking_number" value={form.tracking_number} onChange={handleChange} placeholder="Tracking Number" className="w-full border rounded px-2 py-1" required />
                    <input name="carrier" value={form.carrier} onChange={handleChange} placeholder="Carrier" className="w-full border rounded px-2 py-1" required />
                    <select name="status" value={form.status} onChange={handleChange} className="w-full border rounded px-2 py-1">
                        {STATUS_OPTIONS.map(opt => (
                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                    </select>
                    <input name="estimated_delivery" value={form.estimated_delivery} onChange={handleChange} placeholder="Estimated Delivery (YYYY-MM-DD)" className="w-full border rounded px-2 py-1" type="date" />
                    <input name="actual_delivery" value={form.actual_delivery} onChange={handleChange} placeholder="Actual Delivery (YYYY-MM-DD)" className="w-full border rounded px-2 py-1" type="date" />
                    <input name="recipient_name" value={form.recipient_name} onChange={handleChange} placeholder="Recipient Name" className="w-full border rounded px-2 py-1" />
                    <input name="recipient_address" value={form.recipient_address} onChange={handleChange} placeholder="Recipient Address" className="w-full border rounded px-2 py-1" />
                    <input name="shipper_name" value={form.shipper_name} onChange={handleChange} placeholder="Shipper Name" className="w-full border rounded px-2 py-1" />
                    <textarea name="package_description" value={form.package_description} onChange={handleChange} placeholder="Package Description" className="w-full border rounded px-2 py-1" />
                    <input name="order_number" value={form.order_number} onChange={handleChange} placeholder="Order Number" className="w-full border rounded px-2 py-1" />
                    <input name="tracking_link" value={form.tracking_link} onChange={handleChange} placeholder="Tracking Link" className="w-full border rounded px-2 py-1" />
                    <input name="email_message_id" value={form.email_message_id} onChange={handleChange} placeholder="Email Message ID" className="w-full border rounded px-2 py-1" />
                    {error && <div className="text-red-600 text-sm">{error}</div>}
                    <div className="flex justify-end gap-2 pt-2">
                        <button type="button" className="bg-gray-200 px-4 py-2 rounded hover:bg-gray-300" onClick={onClose} disabled={loading}>Cancel</button>
                        <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700" disabled={loading}>{loading ? 'Adding...' : 'Add'}</button>
                    </div>
                </form>
            </div>
        </div>
    );
}
