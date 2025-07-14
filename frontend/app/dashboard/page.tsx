'use client';

import AppLayout from '@/components/layout/app-layout';
import Sidebar, { Tool } from '@/components/layout/sidebar';
import { useSession } from 'next-auth/react';
import { useState } from 'react';

export default function DashboardPage() {
    const { data: session, status } = useSession();
    const [activeTool, setActiveTool] = useState<Tool>('calendar');

    if (status === 'loading') {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-600"></div>
            </div>
        );
    }

    if (!session) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <h1 className="text-2xl font-bold mb-4">Authentication Required</h1>
                    <p>Please sign in to access your dashboard</p>
                </div>
            </div>
        );
    }

    return (
        <AppLayout
            sidebar={<Sidebar activeTool={activeTool} onToolChange={setActiveTool} />}
            main={
                <div className="p-8">
                    <h1 className="text-3xl font-bold mb-4">Dashboard</h1>
                    <p>Welcome back, {session.user?.name || 'User'}!</p>
                    <p>Status: {status}</p>
                </div>
            }
            draft={<div className="p-4">Simple Draft Pane</div>}
        />
    );
} 