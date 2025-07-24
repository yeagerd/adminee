"use client";
import { useEffect, useState } from "react";

interface TimeSlot {
    id: string;
    start_time: string;
    end_time: string;
}

interface Poll {
    id: string;
    title: string;
    description?: string;
    time_slots: TimeSlot[];
}

export default function PublicPollResponsePage({ params }: { params: { token: string } }) {
    const [poll, setPoll] = useState<Poll | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [participantEmail, setParticipantEmail] = useState("");
    const [responses, setResponses] = useState<Record<string, string>>({});
    const [submitting, setSubmitting] = useState(false);
    const [submitted, setSubmitted] = useState(false);

    useEffect(() => {
        setLoading(true);
        fetch(`/api/public/polls/${params.token}`)
            .then(async (res) => {
                if (!res.ok) throw new Error(await res.text());
                return res.json();
            })
            .then((data) => setPoll(data as Poll))
            .catch((e: unknown) => {
                if (e && typeof e === 'object' && 'message' in e) {
                    setError((e as { message?: string }).message || "Failed to load poll");
                } else {
                    setError("Failed to load poll");
                }
            })
            .finally(() => setLoading(false));
    }, [params.token]);

    const handleResponseChange = (slotId: string, value: string) => {
        setResponses((prev) => ({ ...prev, [slotId]: value }));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitting(true);
        setError(null);
        try {
            const resp = await fetch(`/api/public/polls/${params.token}/respond`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    participantEmail,
                    responses: Object.entries(responses).map(([timeSlotId, response]) => ({ time_slot_id: timeSlotId, response })),
                }),
            });
            if (!resp.ok) throw new Error(await resp.text());
            setSubmitted(true);
        } catch (e: unknown) {
            if (e && typeof e === 'object' && 'message' in e) {
                setError((e as { message?: string }).message || "Failed to submit response");
            } else {
                setError("Failed to submit response");
            }
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) return <div className="p-8 text-center">Loading...</div>;
    if (error) return <div className="p-8 text-center text-red-600">{error}</div>;
    if (!poll) return null;
    if (submitted) return <div className="p-8 text-center text-green-700 font-semibold">Thank you for your response!</div>;

    return (
        <div className="max-w-md mx-auto p-4 sm:p-8 bg-white shadow rounded mt-8 mb-8">
            <h1 className="text-xl sm:text-2xl font-bold mb-2 text-center">{poll.title}</h1>
            <div className="text-gray-600 mb-4 text-center">{poll.description}</div>
            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label className="block font-semibold mb-1">Your Email</label>
                    <input
                        className="w-full border rounded px-3 py-2"
                        type="email"
                        value={participantEmail}
                        onChange={e => setParticipantEmail(e.target.value)}
                        required
                    />
                </div>
                <div>
                    <label className="block font-semibold mb-2">Select your availability:</label>
                    <div className="space-y-2">
                        {(poll.time_slots || []).map((slot) => (
                            <div key={slot.id} className="flex flex-col sm:flex-row sm:items-center gap-2 border-b pb-2">
                                <div className="flex-1">
                                    <span className="font-mono text-sm">{slot.start_time?.slice(0, 16).replace("T", " ")} - {slot.end_time?.slice(11, 16)}</span>
                                </div>
                                <div className="flex gap-2">
                                    {["available", "maybe", "unavailable"].map((val) => (
                                        <label key={val} className="inline-flex items-center">
                                            <input
                                                type="radio"
                                                name={`slot-${slot.id}`}
                                                value={val}
                                                checked={responses[slot.id] === val}
                                                onChange={() => handleResponseChange(slot.id, val)}
                                                required
                                            />
                                            <span className="ml-1 text-xs capitalize">{val}</span>
                                        </label>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
                {error && <div className="text-red-600">{error}</div>}
                <button
                    type="submit"
                    className="w-full bg-teal-600 text-white py-2 rounded font-semibold hover:bg-teal-700"
                    disabled={submitting}
                >
                    {submitting ? "Submitting..." : "Submit Response"}
                </button>
            </form>
        </div>
    );
} 