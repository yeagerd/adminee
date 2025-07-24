"use client";
import gatewayClient from "@/lib/gateway-client";
import Link from "next/link";
import { useEffect, useState } from "react";

function getSlotStats(poll: any) {
    // Returns {slotId: {available: n, maybe: n, unavailable: n}}
    const stats: Record<string, { available: number; maybe: number; unavailable: number }> = {};
    (poll.time_slots || []).forEach((slot: any) => {
        stats[slot.id] = { available: 0, maybe: 0, unavailable: 0 };
    });
    (poll.responses || []).forEach((resp: any) => {
        if (stats[resp.time_slot_id]) {
            stats[resp.time_slot_id][resp.response]++;
        }
    });
    return stats;
}

export default function MeetingPollResultsPage({ params }: { params: { id: string } }) {
    const [poll, setPoll] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        setLoading(true);
        gatewayClient.getMeetingPoll(params.id)
            .then(setPoll)
            .catch((e) => setError(e.message || "Failed to load poll"))
            .finally(() => setLoading(false));
    }, [params.id]);

    let slotStats = poll ? getSlotStats(poll) : {};
    let totalParticipants = poll?.participants?.length || 0;
    let responded = poll?.participants?.filter((p: any) => p.status === "responded").length || 0;

    return (
        <div className="max-w-2xl mx-auto p-8">
            <Link href="/dashboard/meetings" className="text-teal-600 hover:underline mb-4 inline-block">&larr; Back to Meeting Polls</Link>
            <h1 className="text-2xl font-bold mb-6">Meeting Poll Results</h1>
            {loading ? (
                <div>Loading...</div>
            ) : error ? (
                <div className="text-red-600">{error}</div>
            ) : poll ? (
                <div className="bg-white border rounded shadow p-6">
                    <h2 className="text-xl font-semibold mb-2">{poll.title}</h2>
                    <div className="mb-2 text-gray-600">Status: <span className="capitalize">{poll.status}</span></div>
                    <div className="mb-2 text-gray-600">Created: {poll.created_at?.slice(0, 10) || ""}</div>
                    <div className="mb-2 text-gray-600">Location: {poll.location || "-"}</div>
                    <div className="mb-2 text-gray-600">Participants: {totalParticipants} (Responded: {responded})</div>
                    <div className="mb-4">
                        <b>Participant Status:</b>
                        <ul className="ml-4 list-disc">
                            {(poll.participants || []).map((p: any) => (
                                <li key={p.id}>{p.email} <span className="text-xs text-gray-500">({p.status})</span></li>
                            ))}
                        </ul>
                    </div>
                    <div className="mb-4">
                        <b>Time Slot Popularity:</b>
                        <div className="overflow-x-auto">
                            <table className="min-w-full text-xs border">
                                <thead>
                                    <tr>
                                        <th className="px-2 py-1 border">Time Slot</th>
                                        <th className="px-2 py-1 border">Available</th>
                                        <th className="px-2 py-1 border">Maybe</th>
                                        <th className="px-2 py-1 border">Unavailable</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(poll.time_slots || []).map((slot: any) => (
                                        <tr key={slot.id}>
                                            <td className="px-2 py-1 border font-mono">{slot.start_time?.slice(0, 16).replace("T", " ")} - {slot.end_time?.slice(11, 16)}</td>
                                            <td className="px-2 py-1 border text-green-700 font-bold">{slotStats[slot.id]?.available || 0}</td>
                                            <td className="px-2 py-1 border text-yellow-700">{slotStats[slot.id]?.maybe || 0}</td>
                                            <td className="px-2 py-1 border text-red-700">{slotStats[slot.id]?.unavailable || 0}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            ) : null}
        </div>
    );
} 