'use client';

import { Button } from '@/components/ui/button';
import { useAIDrafts } from '@/hooks/use-ai-drafts';
import { useDraftActions } from '@/hooks/use-draft-actions';
import { useDraftState } from '@/hooks/use-draft-state';
import { AIDraftSuggestion } from '@/services/ai-draft-service';
import { Sparkles, Wand2 } from 'lucide-react';
import { useState } from 'react';
import { AIDraftIndicator } from './ai-draft-indicator';
import { AISuggestions } from './ai-suggestions';
import { DraftActions } from './draft-actions';
import { DraftEditor } from './draft-editor';
import { DraftMetadata } from './draft-metadata';
import { DraftTypeSwitcher } from './draft-type-switcher';

export function DraftPane() {
    const {
        state: { currentDraft },
        updateDraft: updateDraftState,
        updateDraftMetadata,
        createNewDraft,
    } = useDraftState();

    const {
        isExecuting,
    } = useDraftActions();

    const {
        isGenerating,
        isImproving,
        currentSuggestions,
        generateDraft,
        improveDraft,
        generateSuggestions,
        approveAIDraft,
        rejectAIDraft,
        applySuggestion,
        clearSuggestions,
    } = useAIDrafts({
        onDraftGenerated: (newDraft) => {
            updateDraftState(newDraft);
        },
        onDraftImproved: (improvedDraft) => {
            updateDraftState(improvedDraft);
        },
        onError: (error) => {
            console.error('AI Draft Error:', error);
        },
    });

    const [showAIPrompt, setShowAIPrompt] = useState(false);
    const [aiPrompt, setAiPrompt] = useState('');

    const handleGenerateAIDraft = async () => {
        if (!currentDraft || !aiPrompt.trim()) return;

        const result = await generateDraft({
            type: currentDraft.type,
            prompt: aiPrompt,
            context: currentDraft.content,
            metadata: currentDraft.metadata as Record<string, unknown>,
            threadId: currentDraft.threadId,
        });

        if (result) {
            setShowAIPrompt(false);
            setAiPrompt('');
        }
    };

    const handleImproveDraft = async () => {
        if (!currentDraft || !aiPrompt.trim()) return;

        const result = await improveDraft(currentDraft.id, aiPrompt);
        if (result) {
            setShowAIPrompt(false);
            setAiPrompt('');
        }
    };

    const handleGenerateSuggestions = async () => {
        if (!currentDraft) return;
        await generateSuggestions(currentDraft);
    };

    const handleApplySuggestion = async (suggestion: AIDraftSuggestion) => {
        if (!currentDraft) return;
        await applySuggestion(suggestion, currentDraft);
    };

    const handleApproveAIDraft = async () => {
        if (!currentDraft) return;
        await approveAIDraft(currentDraft.id);
    };

    const handleRejectAIDraft = async () => {
        if (!currentDraft) return;
        await rejectAIDraft(currentDraft.id, 'User rejected');
    };

    if (!currentDraft) {
        return (
            <div className="flex flex-col h-full p-4">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold">Draft</h2>
                    <Button onClick={() => createNewDraft('email', 'user')} size="sm">
                        New Draft
                    </Button>
                </div>
                <div className="flex-1 flex items-center justify-center text-gray-500">
                    No draft selected
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b">
                <div className="flex items-center gap-2">
                    <h2 className="text-lg font-semibold">Draft</h2>
                    <AIDraftIndicator
                        isAIGenerated={currentDraft.isAIGenerated}
                        status={currentDraft.metadata.ai_status}
                        showActions={currentDraft.isAIGenerated && currentDraft.metadata.ai_status === 'pending'}
                        onApprove={handleApproveAIDraft}
                        onReject={handleRejectAIDraft}
                    />
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowAIPrompt(!showAIPrompt)}
                        disabled={isGenerating || isImproving}
                    >
                        <Sparkles className="h-4 w-4 mr-1" />
                        {showAIPrompt ? 'Cancel' : 'AI Help'}
                    </Button>
                    <Button onClick={() => createNewDraft('email', 'user')} size="sm">
                        New Draft
                    </Button>
                </div>
            </div>

            {/* AI Prompt Input */}
            {showAIPrompt && (
                <div className="p-4 border-b bg-gray-50">
                    <div className="space-y-3">
                        <div className="flex items-center gap-2">
                            <Wand2 className="h-4 w-4 text-purple-500" />
                            <span className="text-sm font-medium">AI Assistant</span>
                        </div>
                        <textarea
                            value={aiPrompt}
                            onChange={(e) => setAiPrompt(e.target.value)}
                            placeholder="Describe what you want to create or how to improve the current draft..."
                            className="w-full p-2 border rounded-md text-sm resize-none"
                            rows={3}
                        />
                        <div className="flex items-center gap-2">
                            <Button
                                onClick={handleGenerateAIDraft}
                                disabled={!aiPrompt.trim() || isGenerating}
                                size="sm"
                            >
                                {isGenerating ? 'Generating...' : 'Generate Draft'}
                            </Button>
                            <Button
                                onClick={handleImproveDraft}
                                disabled={!aiPrompt.trim() || isImproving}
                                variant="outline"
                                size="sm"
                            >
                                {isImproving ? 'Improving...' : 'Improve Draft'}
                            </Button>
                            <Button
                                onClick={handleGenerateSuggestions}
                                disabled={!currentDraft.content}
                                variant="ghost"
                                size="sm"
                            >
                                Get Suggestions
                            </Button>
                        </div>
                    </div>
                </div>
            )}

            {/* AI Suggestions */}
            {currentSuggestions.length > 0 && (
                <div className="p-4 border-b bg-blue-50">
                    <AISuggestions
                        suggestions={currentSuggestions}
                        onApplySuggestion={handleApplySuggestion}
                        onDismissSuggestion={() => {
                            clearSuggestions();
                        }}
                        onGenerateMore={handleGenerateSuggestions}
                    />
                </div>
            )}

            {/* Draft Content */}
            <div className="flex-1 flex flex-col min-h-0">
                <div className="p-4 border-b">
                    <DraftTypeSwitcher
                        currentType={currentDraft.type}
                        onTypeChange={(type) => updateDraftState({ ...currentDraft, type })}
                    />
                </div>

                <div className="p-4 border-b">
                    <DraftMetadata
                        draft={currentDraft}
                        onUpdate={updateDraftMetadata}
                        type={currentDraft.type}
                    />
                </div>

                <div className="flex-1 min-h-0">
                    <DraftEditor
                        type={currentDraft.type}
                        content={currentDraft.content}
                        onUpdate={(content) => updateDraftState({ ...currentDraft, content })}
                        onAutoSave={(content) => updateDraftState({ ...currentDraft, content })}
                        disabled={isExecuting}
                    />
                </div>

                <div className="p-4 border-t">
                    <DraftActions
                        draft={currentDraft}
                        onActionComplete={(action, success) => {
                            if (success) {
                                console.log(`${action} completed successfully`);
                            } else {
                                console.error(`${action} failed`);
                            }
                        }}
                    />
                </div>
            </div>
        </div>
    );
} 