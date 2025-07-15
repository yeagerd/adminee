'use client';

import { useDraftState } from '@/hooks/use-draft-state';
import { cn } from '@/lib/utils';
import { DraftType } from '@/types/draft';
import { AIIndicator } from './ai-indicator';
import { DraftActions } from './draft-actions';
import { DraftEditor } from './draft-editor';
import { DraftMetadata } from './draft-metadata';
import { DraftTypeSwitcher } from './draft-type-switcher';

interface DraftPaneProps {
    className?: string;
    userId?: string;
}

export function DraftPane({ className, userId }: DraftPaneProps) {
    const {
        state: { currentDraft, isLoading, error },
        updateDraft,
        updateDraftMetadata,
        clearDraft,
        createNewDraft,
    } = useDraftState();

    const handleTypeChange = (type: DraftType) => {
        if (currentDraft && currentDraft.type !== type) {
            // If there's unsaved content, ask for confirmation
            if (currentDraft.content.trim() || Object.keys(currentDraft.metadata).length > 0) {
                if (confirm('You have unsaved changes. Are you sure you want to switch draft types?')) {
                    createNewDraft(type, userId || 'anonymous');
                }
            } else {
                createNewDraft(type, userId || 'anonymous');
            }
        } else if (!currentDraft) {
            createNewDraft(type, userId || 'anonymous');
        }
    };

    const handleSave = () => {
        // TODO: Implement save functionality
        console.log('Saving draft:', currentDraft);
    };

    const handleDiscard = () => {
        if (confirm('Are you sure you want to discard this draft?')) {
            clearDraft();
        }
    };

    const handleSend = () => {
        // TODO: Implement send functionality
        console.log('Sending draft:', currentDraft);
    };

    const handleCreate = () => {
        // TODO: Implement create functionality
        console.log('Creating from draft:', currentDraft);
    };

    const handleContentChange = (content: string) => {
        if (currentDraft) {
            updateDraft({ content });
        }
    };

    const handleMetadataChange = (metadata: Partial<import('@/types/draft').DraftMetadata>) => {
        if (currentDraft) {
            updateDraftMetadata(metadata);
        }
    };

    const handleAutoSave = (content: string) => {
        if (currentDraft) {
            updateDraft({ content });
            // TODO: Implement actual auto-save to backend
            console.log('Auto-saving draft:', content);
        }
    };

    if (!currentDraft) {
        return (
            <div className={cn(
                'h-full flex flex-col items-center justify-center p-6 text-center',
                className
            )}>
                <div className="max-w-sm space-y-4">
                    <div className="text-muted-foreground">
                        <h3 className="text-lg font-medium mb-2">No Draft Selected</h3>
                        <p className="text-sm">
                            Create a new draft or select an existing one to get started.
                        </p>
                    </div>

                    <div className="space-y-2">
                        <p className="text-xs text-muted-foreground">Choose a draft type:</p>
                        <DraftTypeSwitcher
                            currentType="email"
                            onTypeChange={handleTypeChange}
                            className="justify-center"
                        />
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className={cn(
            'h-full flex flex-col bg-background',
            className
        )}>
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b">
                <div className="flex items-center gap-3">
                    <DraftTypeSwitcher
                        currentType={currentDraft.type}
                        onTypeChange={handleTypeChange}
                    />
                    {currentDraft.isAIGenerated && (
                        <AIIndicator isAIGenerated={true} size="sm" />
                    )}
                </div>

                <div className="text-xs text-muted-foreground">
                    {currentDraft.updatedAt && (
                        <span>
                            Last updated: {new Date(currentDraft.updatedAt).toLocaleTimeString()}
                        </span>
                    )}
                </div>
            </div>

            {/* Error Display */}
            {error && (
                <div className="p-4 bg-destructive/10 border-b border-destructive/20">
                    <p className="text-sm text-destructive">{error}</p>
                </div>
            )}

            {/* Metadata */}
            <DraftMetadata
                draft={currentDraft}
                onUpdate={handleMetadataChange}
                type={currentDraft.type}
            />

            {/* Content Editor */}
            <div className="flex-1 overflow-hidden">
                <DraftEditor
                    type={currentDraft.type}
                    content={currentDraft.content}
                    onUpdate={handleContentChange}
                    onAutoSave={handleAutoSave}
                    disabled={isLoading}
                />
            </div>

            {/* Actions */}
            <DraftActions
                draft={currentDraft}
                onSave={handleSave}
                onDiscard={handleDiscard}
                onSend={handleSend}
                onCreate={handleCreate}
                isLoading={isLoading}
            />
        </div>
    );
} 