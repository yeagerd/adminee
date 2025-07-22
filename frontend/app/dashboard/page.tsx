'use client';

import ChatInterface from '@/components/chat-interface';
import AppLayout from '@/components/layout/app-layout';
import { DraftPane } from '@/components/draft/draft-pane';
import Sidebar from '@/components/layout/sidebar';
import { ToolContent } from '@/components/tool-content';
import { ToolProvider } from '@/contexts/tool-context';
import { useDraftState } from '@/hooks/use-draft-state';
import { useSession } from 'next-auth/react';
import { Suspense } from 'react';

function DashboardContent() {
    const { data: session, status } = useSession();
    const { state: draftState, setCurrentDraft } = useDraftState();

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

                    {/* Draft Pane - Bottom portion */}
                    <div className="h-80 border-t bg-card">
                        <div className="flex items-center justify-between p-4 border-b">
                            <h2 className="text-lg font-semibold">Chat</h2>
                        </div>
                        <div className="flex-1 overflow-hidden">
                            <ChatInterface onDraftReceived={setCurrentDraft} />
                        </div>
                    </div>
                </div>
            }
            draft={<DraftPane draft={draftState.currentDraft} />}
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