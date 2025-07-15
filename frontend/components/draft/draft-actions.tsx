'use client';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { Draft, DraftType } from '@/types/draft';
import { Plus, Save, Send, Trash2 } from 'lucide-react';

interface DraftActionsProps {
    draft: Draft;
    onSave: () => void;
    onDiscard: () => void;
    onSend?: () => void;
    onCreate?: () => void;
    isLoading?: boolean;
    className?: string;
}

export function DraftActions({
    draft,
    onSave,
    onDiscard,
    onSend,
    onCreate,
    isLoading = false,
    className
}: DraftActionsProps) {
    const getActionButton = () => {
        switch (draft.type) {
            case 'email':
                return (
                    <Button
                        onClick={onSend}
                        disabled={isLoading || !draft.metadata.subject || !draft.metadata.recipients?.length}
                        className="flex items-center gap-2"
                    >
                        <Send className="w-4 h-4" />
                        Send
                    </Button>
                );
            case 'calendar':
                return (
                    <Button
                        onClick={onCreate}
                        disabled={isLoading || !draft.metadata.title || !draft.metadata.startTime}
                        className="flex items-center gap-2"
                    >
                        <Plus className="w-4 h-4" />
                        Create Event
                    </Button>
                );
            case 'document':
                return (
                    <Button
                        onClick={onSave}
                        disabled={isLoading || !draft.metadata.title}
                        className="flex items-center gap-2"
                    >
                        <Save className="w-4 h-4" />
                        Save Document
                    </Button>
                );
            default:
                return null;
        }
    };



    return (
        <div className={cn(
            'flex items-center justify-between p-4 border-t bg-muted/30',
            className
        )}>
            <div className="flex items-center gap-2">
                <Button
                    variant="outline"
                    onClick={onSave}
                    disabled={isLoading}
                    className="flex items-center gap-2"
                >
                    <Save className="w-4 h-4" />
                    Save Draft
                </Button>

                <Button
                    variant="ghost"
                    onClick={onDiscard}
                    disabled={isLoading}
                    className="flex items-center gap-2 text-destructive hover:text-destructive"
                >
                    <Trash2 className="w-4 h-4" />
                    Discard
                </Button>
            </div>

            <div className="flex items-center gap-2">
                {getActionButton()}
            </div>
        </div>
    );
}

export function DraftActionButton({
    type,
    onClick,
    disabled = false,
    isLoading = false,
    className
}: {
    type: DraftType;
    onClick: () => void;
    disabled?: boolean;
    isLoading?: boolean;
    className?: string;
}) {
    const getButtonProps = () => {
        switch (type) {
            case 'email':
                return {
                    icon: Send,
                    label: 'Send',
                    variant: 'default' as const,
                };
            case 'calendar':
                return {
                    icon: Plus,
                    label: 'Create',
                    variant: 'default' as const,
                };
            case 'document':
                return {
                    icon: Save,
                    label: 'Save',
                    variant: 'default' as const,
                };
            default:
                return {
                    icon: Save,
                    label: 'Save',
                    variant: 'default' as const,
                };
        }
    };

    const { icon: Icon, label, variant } = getButtonProps();

    return (
        <Button
            variant={variant}
            onClick={onClick}
            disabled={disabled || isLoading}
            className={cn('flex items-center gap-2', className)}
        >
            <Icon className="w-4 h-4" />
            {isLoading ? 'Loading...' : label}
        </Button>
    );
} 