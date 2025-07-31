import { EmailMessage, EmailThread as EmailThreadType } from '@/types/office-service';
import React from 'react';
import EmailThreadCard from './email-thread-card';

interface EmailThreadProps {
    thread?: EmailThreadType;
    emails?: EmailMessage[];
    threadId?: string;
    onSelectMessage?: (messageId: string) => void;
    selectedMessageId?: string;
}

const EmailThread: React.FC<EmailThreadProps> = ({
    thread,
    emails,
    threadId,
    onSelectMessage,
    selectedMessageId
}) => {
    // Determine which messages to use
    const messages = thread?.messages || emails || [];

    // Handle null/undefined messages
    if (!messages || messages.length === 0) {
        return (
            <div className="p-4 text-center text-gray-500 dark:text-gray-400">
                No thread data available
            </div>
        );
    }

    // Sort messages by date (oldest first for threading)
    const sortedMessages = [...messages].sort((a, b) =>
        new Date(a.date).getTime() - new Date(b.date).getTime()
    );

    return (
        <div className="space-y-4">
            <div className="border-b pb-2 mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                    {thread?.subject || messages[0]?.subject || 'No Subject'}
                </h3>
                <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400 mt-1">
                    <span>{thread?.participant_count || messages.length} participants</span>
                    <span>•</span>
                    <span>{messages.length} messages</span>
                    <span>•</span>
                    <span>
                        {thread?.last_message_date
                            ? new Date(thread.last_message_date).toLocaleDateString()
                            : messages.length > 0
                                ? new Date(messages[messages.length - 1].date).toLocaleDateString()
                                : 'No date'
                        }
                    </span>
                </div>
            </div>

            {sortedMessages.length > 0 ? (
                sortedMessages.map((message, index) => (
                    <EmailThreadCard
                        key={message.id}
                        email={message}
                        isFirstInThread={index === 0}
                        threadId={thread?.id || threadId}
                        isSelected={selectedMessageId === message.id}
                        onSelect={onSelectMessage}
                    />
                ))
            ) : (
                <div className="p-4 text-center text-gray-500 dark:text-gray-400">
                    No messages in this thread
                </div>
            )}
        </div>
    );
};

export default EmailThread;
