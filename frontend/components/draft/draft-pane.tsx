'use client';

import { cn } from '@/lib/utils';
import { Draft, DraftMetadata, DraftType } from '@/types/draft';
import { AIIndicator } from './ai-indicator';
import { DraftActions } from './draft-actions';
import { DraftEditor } from './draft-editor';
import { DraftMetadata as DraftMetadataComponent } from './draft-metadata';
import { DraftTypeSwitcher } from './draft-type-switcher';
import { useDraftState } from '@/hooks/use-draft-state';

interface DraftPaneProps {
    className?: string;
    draft: Draft | null;
    onUpdate: (updates: Partial<Draft>) => void;
    onMetadataChange: (metadata: Partial<DraftMetadata>) => void;
    userId?: string;
}

export function DraftPane({ className, draft, onUpdate, onMetadataChange, userId }: DraftPaneProps) {
    const { createNewDraft } = useDraftState();

    const handleTypeChange = (type: DraftType) => {
        if (draft && draft.type !== type) {
            // If there's unsaved content, ask for confirmation
            if (draft.content.trim() || Object.keys(draft.metadata).length > 0) {
                if (confirm('You have unsaved changes. Are you sure you want to switch draft types?')) {
                    if (userId) createNewDraft(type, userId);
                }
            } else {
                if (userId) createNewDraft(type, userId);
            }
        } else if (!draft) {
            if (userId) createNewDraft(type, userId);
        }
    };

    const handleActionComplete = (action: string, success: boolean) => {
        if (success) {
            console.log(`${action} completed successfully`);
            // TODO: Handle successful actions (e.g., close draft, show success message)
        } else {
            console.error(`${action} failed`);
            // TODO: Handle failed actions (e.g., show error message)
        }
    };

    const handleContentChange = (content: string) => {
        if (draft) {
            onUpdate({ content });
        }
    };

    const handleMetadataChange = (metadata: Partial<DraftMetadata>) => {
        if (draft) {
            onMetadataChange(metadata);
        }
    };

    const handleAutoSave = (content: string) => {
        if (draft) {
            onUpdate({ content });
            // TODO: Implement actual auto-save to backend
            console.log('Auto-saving draft:', content);
        }
    };

    if (!draft) {
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
                        currentType={draft.type}
                        onTypeChange={handleTypeChange}
                    />
                    {draft.isAIGenerated && (
                        <AIIndicator isAIGenerated={true} size="sm" />
                    )}
                </div>

                <div className="text-xs text-muted-foreground">
                    {draft.updatedAt && (
                        <span>
                            Last updated: {new Date(draft.updatedAt).toLocaleTimeString()}
                        </span>
                    )}
                </div>
            </div>

            {/* Metadata */}
            <DraftMetadataComponent
                draft={draft}
                onUpdate={handleMetadataChange}
                type={draft.type}
            />

            {/* Content Editor */}
            <div className="flex-1 overflow-hidden">
                <DraftEditor
                    type={draft.type}
                    content={draft.content}
                    onUpdate={handleContentChange}
                    onAutoSave={handleAutoSave}
                    disabled={false}
                />
            </div>

            {/* Actions */}
            <DraftActions
                draft={draft}
                onActionComplete={handleActionComplete}
            />
        </div>
    );
}