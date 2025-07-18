'use client';

import ChatInterface from '@/components/chat-interface';
import AppLayout from '@/components/layout/app-layout';
import DraftPane from '@/components/layout/draft-pane';
import Sidebar from '@/components/layout/sidebar';
import { ToolContent } from '@/components/tool-content';
import { ToolProvider } from '@/contexts/tool-context';
import { useSession } from 'next-auth/react';
import { Suspense } from 'react';

function DashboardContent() {
    const { data: session, status } = useSession();

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
            sidebar={<Sidebar />}
            main={
                <div className="h-full flex flex-col">
                    {/* Tool Content - Top portion */}
                    <div className="flex-1 overflow-auto">
                        <ToolContent />
                    </div>

                    {/* Chat Interface - Bottom portion */}
                    <div className="h-80 border-t bg-card">
                        <div className="flex items-center justify-between p-4 border-b">
                            <h2 className="text-lg font-semibold">AI Assistant</h2>
                        </div>
                        <div className="flex-1 overflow-hidden">
                            <ChatInterface />
                        </div>
                    </div>
                </div>
            }
            draft={<DraftPane />}
        />
    );
}

export default function DashboardPage() {
    return (
        <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading...</div>}>
            <ToolProvider>
                <DashboardContent />
            </ToolProvider>
        </Suspense>
    );
} 