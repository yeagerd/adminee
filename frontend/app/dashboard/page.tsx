'use client';

import ChatInterface, { DraftData } from '@/components/chat-interface';
import { DraftPane } from '@/components/draft/draft-pane';
import AppLayout from '@/components/layout/app-layout';
import Sidebar from '@/components/layout/sidebar';
import { ToolContent } from '@/components/tool-content';
import { ToolProvider } from '@/contexts/tool-context';
import { useDraftState } from '@/hooks/use-draft-state';
import { convertDraftDataToDraft } from '@/lib/draft-utils';
import { DraftType } from '@/types/draft';
import { useSession } from 'next-auth/react';
import { Suspense } from 'react';

function DashboardContent() {
    const { data: session, status } = useSession();
    const { state: draftState, setCurrentDraft, updateDraft, updateDraftMetadata, createNewDraft, clearDraft } = useDraftState();

    const handleDraftReceived = (draftData: DraftData) => {
        if (session?.user?.email) {
            const newDraft = convertDraftDataToDraft(draftData, session.user.email);
            setCurrentDraft(newDraft);
        }
    };

    const handleTypeChange = (type: DraftType) => {
        if (session?.user?.email) {
            createNewDraft(type, session.user.email);
        }
    }

    // Add a handler for draft actions (send, save, discard)
    const handleDraftActionComplete = (action: string, success: boolean) => {
        if (action === 'discard' && success) {
            clearDraft();
        }
        // Optionally handle other actions (send, save) here
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
            sidebar={<Sidebar />}
            main={
                <div className="h-full flex flex-col">
                    {/* Tool Content - Main portion */}
                    <div className="flex-1 overflow-auto">
                        <ToolContent />
                    </div>
                    {/* Draft Pane - Bottom portion */}
                    <div className="h-80 border-t bg-card">
                        <div className="flex items-center justify-between p-4 border-b">
                            <h2 className="text-lg font-semibold">Draft</h2>
                        </div>
                        <div className="flex-1 overflow-hidden">
                            <DraftPane
                                draft={draftState.currentDraft}
                                onUpdate={updateDraft}
                                onMetadataChange={updateDraftMetadata}
                                onTypeChange={handleTypeChange}
                                isLoading={draftState.isLoading}
                                error={draftState.error}
                                onActionComplete={handleDraftActionComplete}
                            />
                        </div>
                    </div>
                </div>
            }
            draft={<ChatInterface onDraftReceived={handleDraftReceived} />}
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