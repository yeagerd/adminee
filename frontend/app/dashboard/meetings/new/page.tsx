'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function NewMeetingPollRedirectPage() {
    const router = useRouter();

    useEffect(() => {
        // Redirect to the embedded meetings tool with the new poll view
        router.replace('/dashboard?tool=meetings&view=new');
    }, [router]);

    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
            <div className="text-center">
                <h1 className="text-2xl font-bold mb-4">Redirecting...</h1>
                <p>Taking you to the New Meeting Poll Creator</p>
            </div>
        </div>
    );
} 