'use client';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { Draft, DraftMetadata, DraftType } from '@/types/draft';
import { Calendar, FileText, Mail } from 'lucide-react';
import { DraftActions } from './draft-actions';
import { DraftEditor } from './draft-editor';
import { DraftMetadata as DraftMetadataComponent } from './draft-metadata';

interface DraftPaneProps {
    className?: string;
    draft: Draft | null;
    onUpdate: (updates: Partial<Draft>) => void;
    onMetadataChange: (metadata: Partial<DraftMetadata>) => void;
    onTypeChange: (type: DraftType) => void;
    isLoading?: boolean;
    error?: string | null;
    onActionComplete?: (action: string, success: boolean) => void;
}

export function DraftPane({ className, draft, onUpdate, onMetadataChange, onTypeChange, isLoading = false, error = null, onActionComplete }: DraftPaneProps) {
    const draftTypes: { type: DraftType; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
        { type: 'email', label: 'Email', icon: Mail },
        { type: 'calendar', label: 'Calendar', icon: Calendar },
        { type: 'document', label: 'Document', icon: FileText },
    ];

    const handleTypeChange = (type: DraftType) => {
        if (draft && draft.type !== type) {
            // If there's unsaved content, ask for confirmation
            if (draft.content.trim() || Object.keys(draft.metadata).length > 0) {
                if (confirm('You have unsaved changes. Are you sure you want to switch draft types?')) {
                    onTypeChange(type);
                }
            } else {
                onTypeChange(type);
            }
        } else if (!draft) {
            onTypeChange(type);
        }
    };

    const handleActionComplete = (action: string, success: boolean) => {
        if (onActionComplete) {
            onActionComplete(action, success);
        }
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
                'flex flex-col items-center justify-center p-4',
                className
            )}>
                <div className="flex flex-wrap gap-2 justify-center">
                    {draftTypes.map(({ type, label, icon: Icon }) => (
                        <Button
                            key={type}
                            onClick={() => handleTypeChange(type)}
                            className="flex items-center gap-2 px-4 py-2"
                        >
                            <Icon className="h-4 w-4" />
                            {label}
                        </Button>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className={cn(
            'h-full flex flex-col bg-background',
            className
        )}>
            {/* Metadata */}
            <DraftMetadataComponent
                draft={draft}
                onUpdate={handleMetadataChange}
                type={draft.type}
            />

            {/* Error message */}
            {error && (
                <div className="text-sm text-red-500 px-4 py-2">{error}</div>
            )}

            {/* Content Editor */}
            <div className="flex-1 overflow-auto relative">
                {isLoading && (
                    <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/70">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></div>
                    </div>
                )}
                <DraftEditor
                    type={draft.type}
                    content={draft.content}
                    onUpdate={handleContentChange}
                    onAutoSave={handleAutoSave}
                    disabled={isLoading}
                    updatedAt={draft.updatedAt}
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