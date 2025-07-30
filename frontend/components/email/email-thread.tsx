import { EmailMessage } from '@/types/office-service';
import React from 'react';
import EmailCard from './email-card';

interface EmailThreadProps {
    thread: {
        id: string;
        emails: EmailMessage[];
    };
    mode?: 'tight' | 'expanded';
    isSelected?: boolean;
    onSelect?: (threadId: string) => void;
    showReadingPane?: boolean;
}

// Utility function to format email date
const formatEmailDate = (dateString: string): string => {
    const emailDate = new Date(dateString);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const emailDay = new Date(emailDate.getFullYear(), emailDate.getMonth(), emailDate.getDate());

    // If email was sent today, show time
    if (emailDay.getTime() === today.getTime()) {
        return emailDate.toLocaleTimeString([], {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });
    }

    // Otherwise show month and day
    return emailDate.toLocaleDateString([], {
        month: 'short',
        day: 'numeric'
    });
};

const EmailThread: React.FC<EmailThreadProps> = ({
    thread,
    mode = 'expanded',
    isSelected = false,
    onSelect,
    showReadingPane = false
}) => {
    // Sort emails by date (newest first)
    const sortedEmails = [...thread.emails].sort((a, b) =>
        new Date(b.date).getTime() - new Date(a.date).getTime()
    );

    const latestEmail = sortedEmails[0];
    const hasMultipleEmails = sortedEmails.length > 1;

    if (mode === 'tight') {
        return (
            <div className="border-b border-gray-100">
                {/* Main thread row - always shows just the latest email */}
                <div
                    className={`
                        group relative flex items-center gap-3 px-4 py-2 hover:bg-gray-50 cursor-pointer
                        ${isSelected ? 'bg-blue-50 border-l-4 border-l-blue-500' : ''}
                        ${!latestEmail.is_read ? 'bg-blue-50 font-semibold' : ''}
                    `}
                    onClick={() => onSelect?.(thread.id)}
                >
                    {/* Checkbox */}
                    <input
                        type="checkbox"
                        className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                        checked={isSelected}
                        onChange={(e) => e.stopPropagation()}
                    />

                    {/* Star */}
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            // TODO: Implement star functionality
                        }}
                        className="p-1 rounded hover:bg-gray-200 text-gray-400"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                        </svg>
                    </button>

                    {/* Sender */}
                    <div className="flex-shrink-0 w-32 min-w-0">
                        <span className={`block truncate text-xs ${!latestEmail.is_read ? 'font-semibold' : ''}`}>
                            {latestEmail.from_address?.name || latestEmail.from_address?.email || 'Unknown'}
                        </span>
                    </div>

                    {/* Subject and snippet - Single line layout */}
                    <div className="flex-1 min-w-0">
                        <div className="text-xs leading-tight truncate">
                            <span className={`${!latestEmail.is_read ? 'font-semibold' : ''}`}>
                                {latestEmail.subject || '(No subject)'}
                            </span>
                            {hasMultipleEmails && (
                                <span className="text-xs text-gray-500 bg-gray-100 px-1 rounded mx-1">
                                    {sortedEmails.length}
                                </span>
                            )}
                            {latestEmail.has_attachments && (
                                <span className="text-gray-400 mx-1">📎</span>
                            )}
                            <span className="text-gray-500">
                                — {latestEmail.snippet || latestEmail.body_text?.substring(0, 80) || ''}
                            </span>
                        </div>
                    </div>

                    {/* Date and Actions Container */}
                    <div className="flex-shrink-0 w-20 flex items-center justify-end">
                        {/* Date - shown when not hovering */}
                        <span className="text-xs text-gray-500 group-hover:hidden">
                            {formatEmailDate(latestEmail.date)}
                        </span>

                        {/* Hover actions with solid background */}
                        <div className="hidden group-hover:flex items-center gap-1 bg-white rounded shadow-sm border px-1 py-0.5">
                            <button
                                className="h-6 w-6 p-0 hover:bg-gray-100 rounded flex items-center justify-center"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    // TODO: Implement archive functionality
                                }}
                                title="Archive"
                            >
                                <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-14 0h14" />
                                </svg>
                            </button>
                            <button
                                className="h-6 w-6 p-0 hover:bg-gray-100 rounded flex items-center justify-center"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    // TODO: Implement delete functionality
                                }}
                                title="Delete"
                            >
                                <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    // Expanded mode
    return (
        <div className="mb-4">
            {sortedEmails.map((email, index) => (
                <div key={email.id} className={index > 0 ? 'ml-8 border-l-2 border-gray-200 pl-4' : ''}>
                    <EmailCard
                        email={email}
                        onSelect={() => { }} // No expansion toggle for list view
                        showReadingPane={showReadingPane}
                        inlineAvatar={showReadingPane} // Inline avatar in reading pane
                    />
                </div>
            ))}
        </div>
    );
};

export default EmailThread; 