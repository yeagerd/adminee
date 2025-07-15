'use client';

import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import { Editor } from '@tiptap/react';
import {
    Bold,
    Code,
    Heading1,
    Heading2,
    Heading3,
    Image,
    Italic,
    Link,
    List,
    ListOrdered,
    Quote,
    Redo,
    Strikethrough,
    Underline,
    Undo
} from 'lucide-react';

interface EditorToolbarProps {
    editor: Editor | null;
    className?: string;
}

export function EditorToolbar({ editor, className }: EditorToolbarProps) {
    if (!editor) return null;

    const addLink = () => {
        const url = window.prompt('Enter URL');
        if (url) {
            editor.chain().focus().setLink({ href: url }).run();
        }
    };

    const addImage = () => {
        const url = window.prompt('Enter image URL');
        if (url) {
            editor.chain().focus().setImage({ src: url }).run();
        }
    };

    return (
        <div className={cn(
            'flex items-center gap-1 p-2 border-b bg-muted/30',
            className
        )}>
            {/* Text Formatting */}
            <div className="flex items-center gap-1">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => editor.chain().focus().toggleBold().run()}
                    disabled={!editor.can().chain().focus().toggleBold().run()}
                    className={cn(
                        'h-8 w-8 p-0',
                        editor.isActive('bold') && 'bg-muted'
                    )}
                >
                    <Bold className="h-4 w-4" />
                </Button>

                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => editor.chain().focus().toggleItalic().run()}
                    disabled={!editor.can().chain().focus().toggleItalic().run()}
                    className={cn(
                        'h-8 w-8 p-0',
                        editor.isActive('italic') && 'bg-muted'
                    )}
                >
                    <Italic className="h-4 w-4" />
                </Button>

                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => editor.chain().focus().toggleUnderline().run()}
                    className={cn(
                        'h-8 w-8 p-0',
                        editor.isActive('underline') && 'bg-muted'
                    )}
                >
                    <Underline className="h-4 w-4" />
                </Button>

                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => editor.chain().focus().toggleStrike().run()}
                    className={cn(
                        'h-8 w-8 p-0',
                        editor.isActive('strike') && 'bg-muted'
                    )}
                >
                    <Strikethrough className="h-4 w-4" />
                </Button>
            </div>

            <Separator orientation="vertical" className="h-6" />

            {/* Headings */}
            <div className="flex items-center gap-1">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
                    className={cn(
                        'h-8 w-8 p-0',
                        editor.isActive('heading', { level: 1 }) && 'bg-muted'
                    )}
                >
                    <Heading1 className="h-4 w-4" />
                </Button>

                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
                    className={cn(
                        'h-8 w-8 p-0',
                        editor.isActive('heading', { level: 2 }) && 'bg-muted'
                    )}
                >
                    <Heading2 className="h-4 w-4" />
                </Button>

                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
                    className={cn(
                        'h-8 w-8 p-0',
                        editor.isActive('heading', { level: 3 }) && 'bg-muted'
                    )}
                >
                    <Heading3 className="h-4 w-4" />
                </Button>
            </div>

            <Separator orientation="vertical" className="h-6" />

            {/* Lists */}
            <div className="flex items-center gap-1">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => editor.chain().focus().toggleBulletList().run()}
                    className={cn(
                        'h-8 w-8 p-0',
                        editor.isActive('bulletList') && 'bg-muted'
                    )}
                >
                    <List className="h-4 w-4" />
                </Button>

                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => editor.chain().focus().toggleOrderedList().run()}
                    className={cn(
                        'h-8 w-8 p-0',
                        editor.isActive('orderedList') && 'bg-muted'
                    )}
                >
                    <ListOrdered className="h-4 w-4" />
                </Button>
            </div>

            <Separator orientation="vertical" className="h-6" />

            {/* Block Elements */}
            <div className="flex items-center gap-1">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => editor.chain().focus().toggleBlockquote().run()}
                    className={cn(
                        'h-8 w-8 p-0',
                        editor.isActive('blockquote') && 'bg-muted'
                    )}
                >
                    <Quote className="h-4 w-4" />
                </Button>

                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => editor.chain().focus().toggleCodeBlock().run()}
                    className={cn(
                        'h-8 w-8 p-0',
                        editor.isActive('codeBlock') && 'bg-muted'
                    )}
                >
                    <Code className="h-4 w-4" />
                </Button>
            </div>

            <Separator orientation="vertical" className="h-6" />

            {/* Links and Media */}
            <div className="flex items-center gap-1">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={addLink}
                    className={cn(
                        'h-8 w-8 p-0',
                        editor.isActive('link') && 'bg-muted'
                    )}
                >
                    <Link className="h-4 w-4" />
                </Button>

                <Button
                    variant="ghost"
                    size="sm"
                    onClick={addImage}
                    className="h-8 w-8 p-0"
                >
                    {/* eslint-disable-next-line jsx-a11y/alt-text */}
                    <Image className="h-4 w-4" />
                </Button>
            </div>

            <Separator orientation="vertical" className="h-6" />

            {/* History */}
            <div className="flex items-center gap-1">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => editor.chain().focus().undo().run()}
                    disabled={!editor.can().chain().focus().undo().run()}
                    className="h-8 w-8 p-0"
                >
                    <Undo className="h-4 w-4" />
                </Button>

                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => editor.chain().focus().redo().run()}
                    disabled={!editor.can().chain().focus().redo().run()}
                    className="h-8 w-8 p-0"
                >
                    <Redo className="h-4 w-4" />
                </Button>
            </div>
        </div>
    );
} 