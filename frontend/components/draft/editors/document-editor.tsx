'use client';

import { useEditor } from '@/hooks/use-editor';
import { cn } from '@/lib/utils';
import { EditorContent } from '@tiptap/react';
import { EditorToolbar } from '../editor-toolbar';

interface DocumentEditorProps {
    content: string;
    onUpdate: (content: string) => void;
    onAutoSave?: (content: string) => void;
    placeholder?: string;
    className?: string;
    disabled?: boolean;
}

export function DocumentEditor({
    content,
    onUpdate,
    onAutoSave,
    className,
    disabled = false
}: DocumentEditorProps) {
    const { editor, validateContent, getWordCount, getCharacterCount } = useEditor({
        content,
        onUpdate,
        onAutoSave,
        autoSaveDelay: 3000,
    });

    const errors = validateContent(content);
    const wordCount = getWordCount(content);
    const characterCount = getCharacterCount(content);

    return (
        <div className={cn('flex flex-col h-full', className)}>
            {/* Toolbar */}
            <EditorToolbar editor={editor} />

            {/* Editor Content */}
            <div className="flex-1 overflow-auto">
                <div className="p-4 h-full">
                    <EditorContent
                        editor={editor}
                        className={cn(
                            'h-full min-h-[300px] prose prose-sm sm:prose lg:prose-lg xl:prose-2xl max-w-none',
                            'focus:outline-none',
                            disabled && 'opacity-50 pointer-events-none'
                        )}
                    />
                </div>
            </div>

            {/* Status Bar */}
            <div className="flex items-center justify-between p-2 border-t bg-muted/30 text-xs text-muted-foreground">
                <div className="flex items-center gap-4">
                    <span>{wordCount} words</span>
                    <span>{characterCount} characters</span>
                    {errors.length > 0 && (
                        <span className="text-destructive">
                            {errors.length} error{errors.length > 1 ? 's' : ''}
                        </span>
                    )}
                </div>

                {onAutoSave && (
                    <span className="text-green-600">
                        Auto-save enabled
                    </span>
                )}
            </div>

            {/* Error Display */}
            {errors.length > 0 && (
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