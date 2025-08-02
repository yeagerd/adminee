import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { EmailThread as EmailThreadType } from '@/types/office-service';
import { Archive, Clock, Download, MoreHorizontal, Reply, Star, Trash2 } from 'lucide-react';
import React, { useState } from 'react';
import EmailThreadCard from './email-thread-card';

interface EmailThreadProps {
    thread: EmailThreadType;
    onSelectMessage?: (messageId: string) => void;
    selectedMessageId?: string;
}

const EmailThread: React.FC<EmailThreadProps> = ({
    thread,
    onSelectMessage,
    selectedMessageId
}) => {
    const [isStarred, setIsStarred] = useState(false);

    // Handle null/undefined thread or messages
    if (!thread || !thread.messages || thread.messages.length === 0) {
        return (
            <div className="p-4 text-center text-gray-500 dark:text-gray-400">
                No thread data available
            </div>
        );
    }

    // Use the first message for reference
    const firstMessage = thread.messages[0];

    const handleDownload = async () => {
        if (!firstMessage) {
            console.error('No message available for download');
            return;
        }

        try {
            const testData = {
                provider: firstMessage.provider,
                date: firstMessage.date,
                subject: firstMessage.subject,
                sender: firstMessage.from_address?.email || '',
                body_data: {
                    contentType: firstMessage.body_html ? "HTML" : "Text",
                    content: firstMessage.body_html || firstMessage.body_text || ""
                }
            };

            const blob = new Blob([JSON.stringify(testData, null, 2)], {
                type: 'application/json'
            });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `email_test_${firstMessage.id}_${Date.now()}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

        } catch (error) {
            console.error('Failed to download email:', error);
            alert('Failed to download email. Please try again.');
        }
    };



    const handleStarToggle = () => {
        setIsStarred(!isStarred);
        // TODO: Implement actual star functionality
    };

    const handleReply = () => {
        // TODO: Implement reply functionality
        console.log('Reply to thread:', thread.id);
    };

    const handleArchive = () => {
        // TODO: Implement archive functionality
        console.log('Archive thread:', thread.id);
    };

    const handleSnooze = () => {
        // TODO: Implement snooze functionality
        console.log('Snooze thread:', thread.id);
    };

    const handleDelete = () => {
        // TODO: Implement delete functionality
        console.log('Delete thread:', thread.id);
    };

    // Sort messages by date (oldest first for threading)
    const sortedMessages = [...thread.messages].sort((a, b) =>
        new Date(a.date).getTime() - new Date(b.date).getTime()
    );

    return (
        <>
            <div className="space-y-4">
                <div className="border-b pb-2 mb-4">
                    <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                                {thread.subject || 'No Subject'}
                            </h3>
                        </div>

                        {/* Action buttons */}
                        <div className="flex items-center gap-1">
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0"
                                onClick={handleStarToggle}
                                title="Star"
                            >
                                <Star className={`h-4 w-4 ${isStarred ? 'fill-current text-yellow-500' : ''}`} />
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0"
                                onClick={handleSnooze}
                                title="Snooze"
                            >
                                <Clock className="h-4 w-4" />
                            </Button>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0"
                                onClick={handleDelete}
                                title="Delete"
                            >
                                <Trash2 className="h-4 w-4" />
                            </Button>
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-8 w-8 p-0"
                                        title="More actions"
                                    >
                                        <MoreHorizontal className="h-4 w-4" />
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                    <DropdownMenuItem onClick={handleReply}>
                                        <Reply className="h-4 w-4 mr-2" />
                                        Reply
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={handleArchive}>
                                        <Archive className="h-4 w-4 mr-2" />
                                        Archive
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={handleDownload}>
                                        <Download className="h-4 w-4 mr-2" />
                                        Download
                                    </DropdownMenuItem>

                                </DropdownMenuContent>
                            </DropdownMenu>
                        </div>
                    </div>
                </div>

                {sortedMessages.map((message) => (
                    <EmailThreadCard
                        key={message.id}
                        email={message}
                        isSelected={selectedMessageId === message.id}
                        onSelect={onSelectMessage}
                    />
                ))}
            </div>

        </>
    );
};

export default EmailThread;
