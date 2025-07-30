import { EmailMessage } from '@/types/office-service';
import DOMPurify from 'dompurify';
import { Star } from 'lucide-react';
import React from 'react';

// Configure DOMPurify for email content
const emailSanitizeConfig = {
    ALLOWED_TAGS: [
        // Basic text formatting
        'p', 'br', 'div', 'span', 'strong', 'b', 'em', 'i', 'u', 'strike', 's',
        // Headers
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        // Lists
        'ul', 'ol', 'li',
        // Links
        'a',
        // Tables
        'table', 'thead', 'tbody', 'tr', 'td', 'th',
        // Images
        'img',
        // Code
        'code', 'pre',
        // Blockquotes
        'blockquote',
        // Horizontal rule
        'hr'
    ],
    ALLOWED_ATTR: [
        // Link attributes
        'href', 'target', 'rel',
        // Image attributes
        'src', 'alt', 'width', 'height', 'style',
        // Table attributes
        'colspan', 'rowspan', 'align', 'valign',
        // Style attributes (for email formatting)
        'style', 'class', 'id',
        // Common email attributes
        'bgcolor', 'color', 'face', 'size'
    ],
    ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?|mailto|tel|callto|cid|xmpp):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i,
    KEEP_CONTENT: true,
    RETURN_DOM: false,
    RETURN_DOM_FRAGMENT: false,
    RETURN_TRUSTED_TYPE: false
};

// Safe sanitization function with fallback
const sanitizeEmailHtml = (html: string): string => {
    if (!html) return '';

    try {
        // Use DOMPurify if available
        if (typeof DOMPurify !== 'undefined' && DOMPurify.sanitize) {
            return DOMPurify.sanitize(html, emailSanitizeConfig);
        }

        // Fallback: basic sanitization (should rarely be used)
        console.warn('DOMPurify not available, using fallback sanitization');
        return html
            .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
            .replace(/\s*on\w+\s*=\s*["'][^"']*["']/gi, '')
            .replace(/javascript:/gi, '')
            .replace(/data:/gi, '');
    } catch (error) {
        console.error('Error sanitizing HTML:', error);
        return 'Error rendering email content';
    }
};

interface EmailListCardProps {
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

const getSenderInitials = (name?: string, email?: string): string => {
    if (!name && !email) return '?';
    if (name) {
        return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
    }
    return email?.split('@')[0].substring(0, 2).toUpperCase() || '?';
};

const EmailListCard: React.FC<EmailListCardProps> = ({
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
                        <Star className="w-4 h-4" />
                    </button>

                    {/* Sender */}
                    <div className="flex-shrink-0 w-24 min-w-0">
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
                    <div className="flex-shrink-0 w-16 flex items-center justify-end">
                        {/* Date - shown when not hovering */}
                        <span className="text-xs text-gray-500 group-hover:hidden">
                            {formatEmailDate(latestEmail.date)}
                        </span>

                        {/* Action buttons - only visible on hover */}
                        <div className="hidden group-hover:flex items-center gap-1">
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

    // Expanded mode - show different formats based on context
    if (showReadingPane) {
        // Reading pane mode - show full email content with threading
        return (
            <div className="mb-4">
                {sortedEmails.map((email, index) => {
                    const senderName = email.from_address?.name || email.from_address?.email || 'Unknown';
                    const senderInitials = getSenderInitials(email.from_address?.name, email.from_address?.email);
                    const formattedDate = formatEmailDate(email.date);
                    const isUnread = !email.is_read;

                    return (
                        <div key={email.id} className={index > 0 ? 'ml-8 border-l-2 border-gray-200 pl-4' : ''}>
                            <div className="bg-white rounded-lg shadow-sm border p-4 mb-2">
                                {/* Email Header */}
                                <div className="flex items-start gap-3 mb-3">
                                    <div className="flex-shrink-0">
                                        <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                                            <span className="text-blue-600 font-medium text-xs">{senderInitials}</span>
                                        </div>
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className={`font-medium text-sm ${isUnread ? 'font-semibold' : ''}`}>
                                                {senderName}
                                            </span>
                                            {email.has_attachments && (
                                                <span className="text-gray-400 text-xs">📎</span>
                                            )}
                                        </div>
                                        <div className={`text-sm mb-1 ${isUnread ? 'font-semibold' : ''}`}>
                                            {email.subject || '(No subject)'}
                                        </div>
                                        <div className="text-xs text-gray-500">
                                            {formattedDate} • To: {email.to_addresses.map(addr => addr.name || addr.email).join(', ')}
                                        </div>
                                    </div>
                                </div>

                                {/* Email Body */}
                                <div className="ml-11">
                                    {email.body_html ? (
                                        <div
                                            className="prose prose-sm max-w-none text-sm"
                                            style={{
                                                fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                                                fontSize: '14px',
                                                lineHeight: '1.5',
                                                color: '#333'
                                            }}
                                            dangerouslySetInnerHTML={{ __html: sanitizeEmailHtml(email.body_html) }}
                                        />
                                    ) : (
                                        <div className="text-sm text-gray-700">
                                            {email.snippet || email.body_text || 'No preview available'}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        );
    } else {
        // List view mode - show 3-line format for each email in thread
        return (
            <div className="border-b border-gray-100">
                {sortedEmails.map((email, index) => {
                    const senderName = email.from_address?.name || email.from_address?.email || 'Unknown';
                    const senderInitials = getSenderInitials(email.from_address?.name, email.from_address?.email);
                    const formattedDate = formatEmailDate(email.date);
                    const isUnread = !email.is_read;

                    return (
                        <div
                            key={email.id}
                            className={`
                                group relative px-4 py-3 hover:bg-gray-50 cursor-pointer
                                ${isSelected ? 'bg-blue-50 border-l-4 border-l-blue-500' : ''}
                                ${isUnread ? 'bg-blue-50 font-semibold' : ''}
                            `}
                            onClick={() => onSelect?.(thread.id)} // Use thread.id for consistent behavior
                        >
                            {/* Line 1: Sender and Date */}
                            <div className="flex items-center justify-between mb-1">
                                <div className="flex items-center gap-2">
                                    <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                                        <span className="text-blue-600 font-medium text-xs">{senderInitials}</span>
                                    </div>
                                    <span className={`text-sm ${isUnread ? 'font-semibold' : 'font-medium'}`}>
                                        {senderName}
                                    </span>
                                    {email.has_attachments && (
                                        <span className="text-gray-400 text-xs">📎</span>
                                    )}
                                </div>
                                <div className="flex items-center gap-2">
                                    {/* Date - shown when not hovering */}
                                    <span className="text-xs text-gray-500 group-hover:hidden">
                                        {formattedDate}
                                    </span>

                                    {/* Action buttons - only visible on hover */}
                                    <div className="hidden group-hover:flex items-center gap-1">
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

                            {/* Line 2: Subject */}
                            <div className={`text-sm mb-1 truncate ${isUnread ? 'font-semibold' : ''}`}>
                                {email.subject || '(No subject)'}
                            </div>

                            {/* Line 3: Body Preview */}
                            <div className="text-sm text-gray-600 truncate">
                                {email.snippet || email.body_text?.substring(0, 100) || 'No preview available'}
                            </div>
                        </div>
                    );
                })}
            </div>
        );
    }
};

export default EmailListCard; 