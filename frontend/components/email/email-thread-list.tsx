import { EmailThread } from '@/types/office-service';
import React from 'react';
import EmailThreadCard from './email-thread-card';

interface EmailThreadListProps {
    threads: EmailThread[];
    selectedThreadId?: string;
    selectedMessageId?: string;
    onSelectThread?: (threadId: string) => void;
    onSelectMessage?: (messageId: string) => void;
    showReadingPane?: boolean;
}

const EmailThreadList: React.FC<EmailThreadListProps> = ({
    threads,
    selectedThreadId,
    selectedMessageId,
    onSelectThread,
    onSelectMessage,
    showReadingPane = false
}) => {
    const handleThreadClick = (threadId: string) => {
        onSelectThread?.(threadId);
    };

    const handleMessageClick = (messageId: string) => {
        onSelectMessage?.(messageId);
    };

    if (threads.length === 0) {
        return (
            <div className="flex items-center justify-center h-64 text-gray-500 dark:text-gray-400">
                <div className="text-center">
                    <p className="text-lg font-medium">No email threads found</p>
                    <p className="text-sm">Try adjusting your filters or check your email accounts</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-2">
            {threads.map((thread) => {
                const isSelected = selectedThreadId === thread.id;
                const latestMessage = thread.messages[thread.messages.length - 1];

                return (
                    <div
                        key={thread.id}
                        className={`border rounded-lg cursor-pointer transition-colors ${isSelected
                                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                                : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                            }`}
                        onClick={() => handleThreadClick(thread.id)}
                    >
                        <div className="p-4">
                            <div className="flex items-start justify-between mb-2">
                                <div className="flex-1 min-w-0">
                                    <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                                        {thread.subject || 'No Subject'}
                                    </h3>
                                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                        {thread.participant_count} participants • {thread.messages.length} messages
                                    </p>
                                </div>
                                <div className="flex items-center gap-2 ml-2">
                                    {!thread.is_read && (
                                        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                                    )}
                                    <span className="text-xs text-gray-500 dark:text-gray-400">
                                        {new Date(thread.last_message_date).toLocaleDateString()}
                                    </span>
                                </div>
                            </div>

                            {latestMessage && (
                                <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                                    <span className="font-medium">
                                        {latestMessage.from_address?.name || latestMessage.from_address?.email || 'Unknown'}
                                    </span>
                                    <span>•</span>
                                    <span className="truncate">
                                        {latestMessage.snippet || 'No preview available'}
                                    </span>
                                </div>
                            )}
                        </div>

                        {isSelected && showReadingPane && (
                            <div className="border-t border-gray-200 dark:border-gray-700">
                                {thread.messages.map((message, index) => (
                                    <EmailThreadCard
                                        key={message.id}
                                        email={message}
                                        isFirstInThread={index === 0}
                                        threadId={thread.id}
                                        isSelected={selectedMessageId === message.id}
                                        onSelect={handleMessageClick}
                                        inlineAvatar={true}
                                    />
                                ))}
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
};

export default EmailThreadList; 