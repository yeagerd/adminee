'use client';

import { DraftType } from '@/types/draft';
import { CalendarEditor } from './editors/calendar-editor';
import { DocumentEditor } from './editors/document-editor';
import { EmailEditor } from './editors/email-editor';

interface DraftEditorProps {
    type: DraftType;
    content: string;
    onUpdate: (content: string) => void;
    onAutoSave?: (content: string) => void;
    className?: string;
    disabled?: boolean;
    updatedAt?: string;
}

export function DraftEditor({
    type,
    content,
    onUpdate,
    onAutoSave,
    className,
    disabled = false,
    updatedAt
}: DraftEditorProps) {
    const renderEditor = () => {
        switch (type) {
            case 'document':
                return (
                    <DocumentEditor
                        content={content}
                        onUpdate={onUpdate}
                        onAutoSave={onAutoSave}
                        className={className}
                        disabled={disabled}
                        updatedAt={updatedAt}
                    />
                );
            case 'email':
                return (
                    <EmailEditor
                        content={content}
                        onUpdate={onUpdate}
                        onAutoSave={onAutoSave}
                        className={className}
                        disabled={disabled}
                        updatedAt={updatedAt}
                    />
                );
            case 'calendar':
                return (
                    <CalendarEditor
                        content={content}
                        onUpdate={onUpdate}
                        onAutoSave={onAutoSave}
                        className={className}
                        disabled={disabled}
                        updatedAt={updatedAt}
                    />
                );
            default:
                return (
                    <DocumentEditor
                        content={content}
                        onUpdate={onUpdate}
                        onAutoSave={onAutoSave}
                        className={className}
                        disabled={disabled}
                        updatedAt={updatedAt}
                    />
                );
        }
    };

    return renderEditor();
} 