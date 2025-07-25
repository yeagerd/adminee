'use client';

import { useParams, useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function MeetingPollResultsRedirectPage() {
    const router = useRouter();
    const params = useParams();
    const id = params.id as string;

    useEffect(() => {
        if (id) {
            // Redirect to the embedded meetings tool with the specific poll view
            router.replace(`/dashboard?tool=meetings&view=poll&id=${id}`);
        } else {
            router.replace('/dashboard?tool=meetings');
        }
    }, [router, id]);

    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
            <div className="text-center">
                <h1 className="text-2xl font-bold mb-4">Redirecting...</h1>
                <p>Taking you to the Meeting Poll Results</p>
            </div>
        </div>
    );
} 