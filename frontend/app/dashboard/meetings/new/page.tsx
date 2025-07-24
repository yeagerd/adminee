"use client";
import gatewayClient from "@/lib/gateway-client";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function NewMeetingPollPage() {
    const router = useRouter();
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [duration, setDuration] = useState(60);
    const [location, setLocation] = useState("");
    const [participants, setParticipants] = useState("");
    const [timeSlots, setTimeSlots] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        try {
            const pollData = {
                title,
                description,
                duration_minutes: duration,
                location,
                meeting_type: "tbd",
                time_slots: timeSlots.split(",").map((s) => ({ start_time: s.trim(), end_time: s.trim(), timezone: "UTC" })),
                participants: participants.split(",").map((email) => ({ email: email.trim() })),
            };
            await gatewayClient.createMeetingPoll(pollData);
            router.push("/dashboard/meetings");
        } catch (e: any) {
            setError(e.message || "Failed to create poll");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-xl mx-auto p-8">
            <h1 className="text-2xl font-bold mb-6">Create New Meeting Poll</h1>
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
                <div>
                    <label className="block font-semibold mb-1">Participants (comma-separated emails)</label>
                    <input className="w-full border rounded px-3 py-2" value={participants} onChange={e => setParticipants(e.target.value)} required />
                </div>
                <div>
                    <label className="block font-semibold mb-1">Time Slots (comma-separated, e.g. 2024-07-01T10:00,2024-07-01T14:00)</label>
                    <input className="w-full border rounded px-3 py-2" value={timeSlots} onChange={e => setTimeSlots(e.target.value)} required />
                </div>
                {error && <div className="text-red-600">{error}</div>}
                <button type="submit" className="w-full bg-teal-600 text-white py-2 rounded font-semibold hover:bg-teal-700" disabled={loading}>
                    {loading ? "Creating..." : "Create Poll"}
                </button>
            </form>
        </div>
    );
} 