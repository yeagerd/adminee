"use client";
import gatewayClient from "@/lib/gateway-client";
import Link from "next/link";
import { useEffect, useState } from "react";

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
                    <div className="mb-2 text-gray-600">Participants:</div>
                    <ul className="list-disc ml-6">
                        {(poll.participants || []).map((p: any) => (
                            <li key={p.id}>{p.email} {p.status && <span className="text-xs text-gray-500">({p.status})</span>}</li>
                        ))}
                    </ul>
                </div>
            ) : null}
        </div>
    );
} 