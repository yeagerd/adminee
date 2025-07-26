'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useToolStateUtils } from '@/hooks/use-tool-state';
import { gatewayClient, MeetingPoll, MeetingPollUpdate } from '@/lib/gateway-client';
import { ArrowLeft } from 'lucide-react';
import { useEffect, useState } from 'react';

interface MeetingPollEditProps {
    pollId: string;
}

export function MeetingPollEdit({ pollId }: MeetingPollEditProps) {
    const { goBackToPreviousMeetingView, setMeetingSubView } = useToolStateUtils();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [deleting, setDeleting] = useState(false);
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [duration, setDuration] = useState(60);
    const [location, setLocation] = useState("");

    useEffect(() => {
        if (!pollId) return;
        setLoading(true);
        gatewayClient.getMeetingPoll(pollId)
            .then((poll: MeetingPoll) => {
                setTitle(poll.title || "");
                setDescription(poll.description || "");
                setDuration(poll.duration_minutes || 60);
                setLocation(poll.location || "");
            })
            .catch((e) => setError(e.message || "Failed to load poll"))
            .finally(() => setLoading(false));
    }, [pollId]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        setError(null);
        try {
            const updateData: MeetingPollUpdate = {
                title,
                description,
                duration_minutes: duration,
                location,
            };
            await gatewayClient.updateMeetingPoll(pollId, updateData);
            goBackToPreviousMeetingView();
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

    const handleDelete = async () => {
        if (!window.confirm('Are you sure you want to delete this meeting poll?')) return;
        setDeleting(true);
        setError(null);
        try {
            await gatewayClient.deleteMeetingPoll(pollId);
            setMeetingSubView('list');
        } catch (e: unknown) {
            if (e && typeof e === 'object' && 'message' in e) {
                setError((e as { message?: string }).message || "Failed to delete poll");
            } else {
                setError("Failed to delete poll");
            }
        } finally {
            setDeleting(false);
        }
    };

    const handleCancel = () => {
        goBackToPreviousMeetingView();
    };

    if (loading) {
        return (
            <div className="p-8">
                <div className="flex items-center justify-center py-8">
                    <div className="text-gray-500">Loading...</div>
                </div>
            </div>
        );
    }

    return (
        <div className="p-8">
            <div className="flex items-center gap-4 mb-6">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleCancel}
                    className="flex items-center gap-2"
                >
                    <ArrowLeft className="h-4 w-4" />
                    Back
                </Button>
                <h1 className="text-2xl font-bold">Edit Meeting Poll</h1>
            </div>

            <Card>
                <CardContent className="pt-6">
                    {error && (
                        <div className="mb-4 p-3 bg-red-100 border border-red-300 rounded text-red-700">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="block font-semibold mb-1">Title</label>
                            <input
                                className="w-full border rounded px-3 py-2"
                                value={title}
                                onChange={e => setTitle(e.target.value)}
                                required
                            />
                        </div>
                        <div>
                            <label className="block font-semibold mb-1">Description</label>
                            <textarea
                                className="w-full border rounded px-3 py-2"
                                value={description}
                                onChange={e => setDescription(e.target.value)}
                            />
                        </div>
                        <div>
                            <label className="block font-semibold mb-1">Duration (minutes)</label>
                            <input
                                type="number"
                                className="w-full border rounded px-3 py-2"
                                value={duration}
                                onChange={e => setDuration(Number(e.target.value))}
                                min={1}
                                required
                            />
                        </div>
                        <div>
                            <label className="block font-semibold mb-1">Location</label>
                            <input
                                className="w-full border rounded px-3 py-2"
                                value={location}
                                onChange={e => setLocation(e.target.value)}
                            />
                        </div>

                        <div className="flex gap-3 pt-4">
                            <Button
                                type="button"
                                variant="outline"
                                onClick={handleCancel}
                                className="flex-1"
                            >
                                Cancel
                            </Button>
                            <Button
                                type="submit"
                                className="flex-1"
                                disabled={saving}
                            >
                                {saving ? "Saving..." : "Save Changes"}
                            </Button>
                        </div>
                    </form>

                    <div className="pt-6 border-t mt-6">
                        <Button
                            type="button"
                            variant="destructive"
                            onClick={handleDelete}
                            disabled={deleting}
                            className="w-full"
                        >
                            {deleting ? "Deleting..." : "Delete Meeting Poll"}
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
} 