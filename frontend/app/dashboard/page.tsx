'use client';

import AppLayout from '@/components/layout/app-layout';
import Sidebar, { Tool } from '@/components/layout/sidebar';
import { useSession } from 'next-auth/react';
import { useState } from 'react';

export default function DashboardPage() {
    const { data: session, status } = useSession();
    const [activeTool, setActiveTool] = useState<Tool>('calendar');

    const renderToolContent = () => {
        switch (activeTool) {
            case 'calendar':
                return (
                    <div className="p-8">
                        <h1 className="text-3xl font-bold mb-4">Calendar</h1>
                        <p>Calendar view coming soon...</p>
                    </div>
                );
            case 'email':
                return (
                    <div className="p-8">
                        <h1 className="text-3xl font-bold mb-4">Email</h1>
                        <p>Email view coming soon...</p>
                    </div>
                );
            case 'documents':
                return (
                    <div className="p-8">
                        <h1 className="text-3xl font-bold mb-4">Documents</h1>
                        <p>Documents view coming soon...</p>
                    </div>
                );
            case 'tasks':
                return (
                    <div className="p-8">
                        <h1 className="text-3xl font-bold mb-4">Tasks</h1>
                        <p>Tasks view coming soon...</p>
                    </div>
                );
            case 'packages':
                return (
                    <div className="p-8">
                        <h1 className="text-3xl font-bold mb-4">Package Tracker</h1>
                        <p>Package tracker view coming soon...</p>
                    </div>
                );
            case 'research':
                return (
                    <div className="p-8">
                        <h1 className="text-3xl font-bold mb-4">Research</h1>
                        <p>Research view coming soon...</p>
                    </div>
                );
            case 'pulse':
                return (
                    <div className="p-8">
                        <h1 className="text-3xl font-bold mb-4">Pulse</h1>
                        <p>Pulse view coming soon...</p>
                    </div>
                );
            case 'insights':
                return (
                    <div className="p-8">
                        <h1 className="text-3xl font-bold mb-4">Insights</h1>
                        <p>Insights view coming soon...</p>
                    </div>
                );
            default:
                return (
                    <div className="p-8">
                        <h1 className="text-3xl font-bold mb-4">Dashboard</h1>
                        <p>Welcome back, {session?.user?.name || 'User'}!</p>
                    </div>
                );
        }
    };

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
            main={renderToolContent()}
            draft={<div className="p-4">Simple Draft Pane</div>}
        />
    );
} 