import { safeParseDate } from '@/lib/utils';
import { EmailThread as EmailThreadType } from '@/types/office-service';
import React from 'react';
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
    // Handle null/undefined thread or messages
    if (!thread || !thread.messages || thread.messages.length === 0) {
        return (
            <div className="p-4 text-center text-gray-500 dark:text-gray-400">
                No thread data available
            </div>
        );
    }

    // Sort messages by date (oldest first for threading) with defensive date parsing
    const sortedMessages = [...thread.messages].sort((a, b) => {
        const dateA = safeParseDate(a.date);
        const dateB = safeParseDate(b.date);

        // If either date is invalid, put it at the end
        if (!dateA && !dateB) return 0;
        if (!dateA) return 1;
        if (!dateB) return -1;

        return dateA.getTime() - dateB.getTime();
    });

    return (
        <div className="space-y-4">
            <div className="border-b pb-2 mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                    {thread.subject || 'No Subject'}
                </h3>
                <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400 mt-1">
                    <span>{thread.participant_count} participants</span>
                    <span>•</span>
                    <span>{thread.messages.length} messages</span>
                    <span>•</span>
                    <span>
                        {thread.last_message_date
                            ? new Date(thread.last_message_date).toLocaleDateString()
                            : 'No date'
                        }
                    </span>
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
    );
};

export default EmailThread;
