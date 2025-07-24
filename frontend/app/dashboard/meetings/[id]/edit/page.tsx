"use client";
import gatewayClient from "@/lib/gateway-client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

interface Poll {
    title?: string;
    description?: string;
    duration_minutes?: number;
    location?: string;
}

export default function EditMeetingPollPage({ params }: { params: { id: string } }) {
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [duration, setDuration] = useState(60);
    const [location, setLocation] = useState("");

    useEffect(() => {
        setLoading(true);
        gatewayClient.getMeetingPoll(params.id)
            .then((poll) => {
                const p = poll as Poll;
                setTitle(p.title || "");
                setDescription(p.description || "");
                setDuration(p.duration_minutes || 60);
                setLocation(p.location || "");
            })
            .catch((e) => setError(e.message || "Failed to load poll"))
            .finally(() => setLoading(false));
    }, [params.id]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        setError(null);
        try {
            await gatewayClient.updateMeetingPoll(params.id, {
                title,
                description,
                duration_minutes: duration,
                location,
            });
            router.push("/dashboard/meetings");
        } catch (e: unknown) {
            if (e && typeof e === 'object' && 'message' in e) {
                setError((e as { message?: string }).message || "Failed to update poll");
            } else {
                setError("Failed to update poll");
            }
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="max-w-xl mx-auto p-8">
            <h1 className="text-2xl font-bold mb-6">Edit Meeting Poll</h1>
            {loading ? (
                <div>Loading...</div>
            ) : error ? (
                <div className="text-red-600">{error}</div>
            ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block font-semibold mb-1">Title</label>
                        <input className="w-full border rounded px-3 py-2" value={title} onChange={e => setTitle(e.target.value)} required />
                    </div>
                    <div>
                        <label className="block font-semibold mb-1">Description</label>
                        <textarea className="w-full border rounded px-3 py-2" value={description} onChange={e => setDescription(e.target.value)} />
                    </div>
                    <div>
                        <label className="block font-semibold mb-1">Duration (minutes)</label>
                        <input type="number" className="w-full border rounded px-3 py-2" value={duration} onChange={e => setDuration(Number(e.target.value))} min={1} required />
                    </div>
                    <div>
                        <label className="block font-semibold mb-1">Location</label>
                        <input className="w-full border rounded px-3 py-2" value={location} onChange={e => setLocation(e.target.value)} />
                    </div>
                    {error && <div className="text-red-600">{error}</div>}
                    <button type="submit" className="w-full bg-teal-600 text-white py-2 rounded font-semibold hover:bg-teal-700" disabled={saving}>
                        {saving ? "Saving..." : "Save Changes"}
                    </button>
                </form>
            )}
        </div>
    );
} 