'use client';

import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { useDraftActions } from '@/hooks/use-draft-actions';
import { Draft } from '@/types/draft';
import { Loader2, Save, Send, Trash2 } from 'lucide-react';
import { useState } from 'react';

interface DraftActionsProps {
    draft: Draft;
    onActionComplete?: (action: string, success: boolean) => void;
}

export function DraftActions({ draft, onActionComplete }: DraftActionsProps) {
    const { isExecuting, error, executeAction, clearError } = useDraftActions();
    const [showDiscardDialog, setShowDiscardDialog] = useState(false);

    const handleAction = async (action: 'send' | 'save' | 'discard') => {
        if (action === 'discard') {
            setShowDiscardDialog(true);
            return;
        }

        const result = await executeAction(action, draft);
        onActionComplete?.(action, result.success);
    };

    const handleDiscardConfirm = async () => {
        const result = await executeAction('discard', draft);
        setShowDiscardDialog(false);
        onActionComplete?.('discard', result.success);
    };

    const getActionButton = (action: 'send' | 'save' | 'discard') => {
        const isDisabled = isExecuting;
        const isLoading = isExecuting;

        const buttonProps = {
            disabled: isDisabled,
            onClick: () => handleAction(action),
        };

        const iconProps = {
            className: 'h-4 w-4',
        };

        switch (action) {
            case 'send':
                return (
                    <Button {...buttonProps} variant="default" className="flex items-center gap-2">
                        {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send {...iconProps} />}
                        Send
                    </Button>
                );
            case 'save':
                return (
                    <Button {...buttonProps} variant="outline" className="flex items-center gap-2">
                        {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save {...iconProps} />}
                        Save
                    </Button>
                );
            case 'discard':
                return (
                    <Button {...buttonProps} variant="destructive" className="flex items-center gap-2">
                        <Trash2 {...iconProps} />
                        Discard
                    </Button>
                );
        }
    };

    return (
        <div className="flex items-center gap-2">
            {error && (
                <div className="text-sm text-red-500 mb-2">
                    {error}
                    <Button variant="ghost" size="sm" onClick={clearError} className="ml-2">
                        Dismiss
                    </Button>
                </div>
            )}

            <div className="flex gap-2">
                <AlertDialog open={showDiscardDialog} onOpenChange={setShowDiscardDialog}>
                    <AlertDialogTrigger asChild>
                        <Button variant="destructive" className="flex items-center gap-2">
                            <Trash2 className="h-4 w-4" />
                            Discard
                        </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                        <AlertDialogHeader>
                            <AlertDialogTitle>Discard Draft?</AlertDialogTitle>
                            <AlertDialogDescription>
                                This action cannot be undone. This will permanently delete your draft.
                            </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction onClick={handleDiscardConfirm} className="bg-red-600 hover:bg-red-700">
                                Discard
                            </AlertDialogAction>
                        </AlertDialogFooter>
                    </AlertDialogContent>
                </AlertDialog>

                {draft.type === 'email' && (
                    <>
                        {getActionButton('save')}
                        {getActionButton('send')}
                    </>
                )}
                {draft.type === 'document' && getActionButton('save')}
                {draft.type === 'calendar' && getActionButton('save')}
            </div>
        </div>
    );
} 