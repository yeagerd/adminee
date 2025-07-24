import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';

type Poll = { title: string; time_slots?: any[] };
type Participant = { name?: string; email: string };

type PollResponse = { time_slot_id: string; response: string; comment?: string };

export default function PollResponsePage() {
    const router = useRouter();
    const { response_token } = router.query;
    const [poll, setPoll] = useState<Poll | null>(null);
    const [participant, setParticipant] = useState<Participant | null>(null);
    const [responses, setResponses] = useState<PollResponse[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [submitted, setSubmitted] = useState(false);

    useEffect(() => {
        if (!response_token) return;
        fetch(`/api/public/meetings/response/${response_token}`)
            .then(res => res.json())
            .then(data => {
                setPoll(data.poll);
                setParticipant(data.participant);
                setLoading(false);
            })
            .catch(() => {
                setError('Invalid or expired link.');
                setLoading(false);
            });
    }, [response_token]);

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setLoading(true);
        const res = await fetch(`/api/public/meetings/response/${response_token}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ responses }),
        });
        if (res.ok) {
            setSubmitted(true);
        } else {
            setError('Failed to submit response.');
        }
        setLoading(false);
    };

    if (loading) return <div>Loading...</div>;
    if (error) return <div>{error}</div>;
    if (submitted) return <div>Thank you for your response!</div>;

    return (
        <div>
            <h1>Respond to Meeting Poll</h1>
            <h2>{poll?.title}</h2>
            <form onSubmit={handleSubmit}>
                {/* Render time slots and response options here */}
                {/* Example: */}
                {/* poll?.time_slots?.map(slot => ( ... )) */}
                <button type="submit">Submit</button>
            </form>
        </div>
    );
} 