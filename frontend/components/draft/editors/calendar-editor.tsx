'use client';

import { useEditor } from '@/hooks/use-editor';
import { cn } from '@/lib/utils';
import { EditorContent } from '@tiptap/react';
import { useEffect, useState } from 'react';
import type { MouseEvent } from 'react';
import { EditorToolbar } from '../editor-toolbar';

interface CalendarEditorProps {
    content: string;
    onUpdate: (content: string) => void;
    onAutoSave?: (content: string) => void;
    placeholder?: string;
    className?: string;
    disabled?: boolean;
    updatedAt?: string;
}

export function CalendarEditor({
    content,
    onUpdate,
    onAutoSave,
    className,
    disabled = false,
    updatedAt
}: CalendarEditorProps) {
    const { editor, validateContent, getWordCount, getCharacterCount } = useEditor({
        content,
        onUpdate,
        onAutoSave,
        autoSaveDelay: 3000,
    });

    const [hasInteracted, setHasInteracted] = useState(false);
    const [initialMount, setInitialMount] = useState(true);

    // Track user interaction after initial mount
    useEffect(() => {
        if (initialMount) {
            setInitialMount(false);
        } else if (!hasInteracted && content.trim().length > 0) {
            setHasInteracted(true);
        }
    }, [content, hasInteracted, initialMount]);

    const errors = validateContent(content);
    const wordCount = getWordCount(content);
    const characterCount = getCharacterCount(content);
    const showErrors = hasInteracted && errors.length > 0;

    const handleContainerMouseDown = (e: MouseEvent<HTMLDivElement>) => {
        if (!editor || disabled) return;
        const target = e.target as HTMLElement;
        const isInsideProseMirror = !!target.closest('.ProseMirror');
        if (!isInsideProseMirror) {
            e.preventDefault();
            editor.commands.focus('end');
        }
    };

    return (
        <div className={cn('flex flex-col h-full', className)}>
            {/* Toolbar */}
            <EditorToolbar editor={editor} />

            {/* Editor Content */}
            <div className="flex-1 min-h-0 p-4 cursor-text" onMouseDown={handleContainerMouseDown}>
                <EditorContent
                    editor={editor}
                    className={cn(
                        'prose prose-sm sm:prose lg:prose-lg xl:prose-2xl max-w-none',
                        'focus:outline-none',
                        'min-h-[200px]',
                        disabled && 'opacity-50 pointer-events-none'
                    )}
                />
            </div>

            {/* Status Bar */}
            <div className="flex items-center justify-between p-2 border-t bg-muted/30 text-xs text-muted-foreground">
                <div className="flex items-center gap-4">
                    <span>{wordCount} words</span>
                    <span>{characterCount} characters</span>
                    {showErrors && (
                        <span className="text-destructive">
                            {errors.length} error{errors.length > 1 ? 's' : ''}
                        </span>
                    )}
                </div>

                <div className="flex items-center gap-4">
                    {updatedAt && (
                        <span>
                            Last updated: {new Date(updatedAt).toLocaleTimeString()}
                        </span>
                    )}
                    {onAutoSave && (
                        <span className="text-green-600">
                            Auto-save enabled
                        </span>
                    )}
                </div>
            </div>

            {/* Error Display */}
            {showErrors && (
                <div className="p-2 bg-destructive/10 border-t border-destructive/20">
                    <ul className="text-xs text-destructive space-y-1">
                        {errors.map((error, index) => (
                            <li key={index}>• {error}</li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
} 