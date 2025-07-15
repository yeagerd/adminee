'use client';

import CodeBlock from '@tiptap/extension-code-block';
import Highlight from '@tiptap/extension-highlight';
import Image from '@tiptap/extension-image';
import Link from '@tiptap/extension-link';
import Placeholder from '@tiptap/extension-placeholder';
import TaskItem from '@tiptap/extension-task-item';
import TaskList from '@tiptap/extension-task-list';
import { useEditor as useTipTapEditor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { useCallback, useEffect, useRef } from 'react';

interface UseEditorProps {
    content: string;
    onUpdate: (content: string) => void;
    autoSaveDelay?: number;
    onAutoSave?: (content: string) => void;
}

export function useEditor({
    content,
    onUpdate,
    autoSaveDelay = 2000,
    onAutoSave
}: UseEditorProps) {
    const autoSaveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const lastSavedContentRef = useRef(content);

    const editor = useTipTapEditor({
        extensions: [
            StarterKit.configure({
                heading: {
                    levels: [1, 2, 3],
                },
                bulletList: {
                    keepMarks: true,
                    keepAttributes: false,
                },
                orderedList: {
                    keepMarks: true,
                    keepAttributes: false,
                },
            }),
            Placeholder.configure({
                placeholder: 'Start writing...',
            }),
            Link.configure({
                openOnClick: false,
                HTMLAttributes: {
                    class: 'text-primary underline cursor-pointer',
                },
            }),
            Image.configure({
                HTMLAttributes: {
                    class: 'max-w-full h-auto',
                },
            }),
            TaskList,
            TaskItem.configure({
                nested: true,
            }),
            CodeBlock.configure({
                HTMLAttributes: {
                    class: 'bg-muted p-4 rounded-md font-mono text-sm',
                },
            }),
            Highlight.configure({
                HTMLAttributes: {
                    class: 'bg-yellow-200 dark:bg-yellow-800',
                },
            }),
        ],
        content,
        onUpdate: ({ editor }) => {
            const newContent = editor.getHTML();
            onUpdate(newContent);

            // Auto-save functionality
            if (onAutoSave && newContent !== lastSavedContentRef.current) {
                if (autoSaveTimeoutRef.current) {
                    clearTimeout(autoSaveTimeoutRef.current);
                }

                autoSaveTimeoutRef.current = setTimeout(() => {
                    onAutoSave(newContent);
                    lastSavedContentRef.current = newContent;
                }, autoSaveDelay);
            }
        },
        editorProps: {
            attributes: {
                class: 'prose prose-sm sm:prose lg:prose-lg xl:prose-2xl mx-auto focus:outline-none',
            },
        },
        immediatelyRender: false,
    });

    // Cleanup auto-save timeout on unmount
    useEffect(() => {
        return () => {
            if (autoSaveTimeoutRef.current) {
                clearTimeout(autoSaveTimeoutRef.current);
            }
        };
    }, []);

    // Update last saved content when content prop changes
    useEffect(() => {
        lastSavedContentRef.current = content;
    }, [content]);

    const validateContent = useCallback((content: string) => {
        const errors: string[] = [];

        if (!content.trim()) {
            errors.push('Content cannot be empty');
        }

        if (content.length > 10000) {
            errors.push('Content is too long (max 10,000 characters)');
        }

        return errors;
    }, []);

    const getWordCount = useCallback((content: string) => {
        return content.trim().split(/\s+/).filter(word => word.length > 0).length;
    }, []);

    const getCharacterCount = useCallback((content: string) => {
        return content.length;
    }, []);

    const insertText = useCallback((text: string) => {
        if (editor) {
            editor.commands.insertContent(text);
        }
    }, [editor]);

    const clearContent = useCallback(() => {
        if (editor) {
            editor.commands.clearContent();
        }
    }, [editor]);

    const focus = useCallback(() => {
        if (editor) {
            editor.commands.focus();
        }
    }, [editor]);

    return {
        editor,
        validateContent,
        getWordCount,
        getCharacterCount,
        insertText,
        clearContent,
        focus,
        isReady: !!editor,
    };
} 