'use client';

import { cn } from '@/lib/utils';
import { Draft } from '@/types/draft';
import { AIIndicator } from './ai-indicator';
import { DraftActions } from './draft-actions';
import { DraftEditor } from './draft-editor';
import { DraftMetadata } from './draft-metadata';
import { DraftTypeSwitcher } from './draft-type-switcher';

interface DraftPaneProps {
    className?: string;
    draft: Draft | null;
}

export function DraftPane({ className, draft }: DraftPaneProps) {
    const handleTypeChange = () => {
        // TODO: Implement type change logic
    };

    const handleActionComplete = () => {
        // TODO: Implement action complete logic
    };

    const handleContentChange = () => {
        // TODO: Implement content change logic
    };

    const handleMetadataChange = () => {
        // TODO: Implement metadata change logic
    };

    const handleAutoSave = () => {
        // TODO: Implement auto-save logic
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
            <DraftMetadata
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