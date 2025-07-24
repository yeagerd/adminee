"use client";
import gatewayClient from "@/lib/gateway-client";
import Link from "next/link";
import { useEffect, useState } from "react";

export default function MeetingsDashboardPage() {
    const [polls, setPolls] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    const fetchPolls = () => {
        setLoading(true);
        gatewayClient.listMeetingPolls()
            .then(setPolls)
            .catch((e) => setError(e.message || "Failed to load polls"))
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        fetchPolls();
    }, []);

    const handleDelete = async (id: string) => {
        if (!window.confirm("Are you sure you want to delete this meeting poll?")) return;
        setDeletingId(id);
        try {
            await gatewayClient.deleteMeetingPoll(id);
            fetchPolls();
        } catch (e: any) {
            alert(e.message || "Failed to delete poll");
        } finally {
            setDeletingId(null);
        }
    };

    return (
        <div className="p-8">
            <div className="flex items-center justify-between mb-6">
                <h1 className="text-2xl font-bold">Meeting Polls</h1>
                <Link href="/dashboard/meetings/new">
                    <button className="bg-teal-600 text-white px-4 py-2 rounded shadow hover:bg-teal-700 font-semibold">
                        + New Meeting Poll
                    </button>
                </Link>
            </div>
            {loading ? (
                <div>Loading...</div>
            ) : error ? (
                <div className="text-red-600">{error}</div>
            ) : polls.length === 0 ? (
                <div className="text-gray-500">No meeting polls found.</div>
            ) : (
                <table className="min-w-full bg-white border rounded shadow">
                    <thead>
                        <tr>
                            <th className="px-4 py-2 border-b">Title</th>
                            <th className="px-4 py-2 border-b">Status</th>
                            <th className="px-4 py-2 border-b">Created</th>
                            <th className="px-4 py-2 border-b">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {polls.map((poll) => (
                            <tr key={poll.id} className="hover:bg-gray-50">
                                <td className="px-4 py-2 border-b font-medium">{poll.title}</td>
                                <td className="px-4 py-2 border-b capitalize">{poll.status}</td>
                                <td className="px-4 py-2 border-b">{poll.created_at?.slice(0, 10) || ""}</td>
                                <td className="px-4 py-2 border-b space-x-2">
                                    <Link href={`/dashboard/meetings/${poll.id}`} className="text-teal-600 hover:underline font-semibold">
                                        View Results
                                    </Link>
                                    <Link href={`/dashboard/meetings/${poll.id}/edit`} className="text-blue-600 hover:underline font-semibold">
                                        Edit
                                    </Link>
                                    <button
                                        className="text-red-600 hover:underline font-semibold disabled:opacity-50"
                                        onClick={() => handleDelete(poll.id)}
                                        disabled={deletingId === poll.id}
                                    >
                                        {deletingId === poll.id ? "Deleting..." : "Delete"}
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
        </div>
    );
} 