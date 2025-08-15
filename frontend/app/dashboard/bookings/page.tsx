'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function BookingsRedirectPage() {
    const router = useRouter();

    useEffect(() => {
        // Redirect to the embedded bookings tool
        router.replace('/dashboard?tool=bookings');
    }, [router]);

    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
            <div className="text-center">
                <h1 className="text-2xl font-bold mb-4">Redirecting...</h1>
                <p>Taking you to the Bookings tool</p>
            </div>
        </div>
    );
}
