import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { useShipmentDetection } from '@/hooks/use-shipment-detection';
import { shipmentsClient } from '@/lib/shipments-client';
import { EmailMessage } from '@/types/office-service';
import DOMPurify from 'dompurify';
import { Archive, Clock, Download, MoreHorizontal, Reply, Star, Trash2, Wand2 } from 'lucide-react';
import React, { useState } from 'react';
import { toast } from 'sonner';
import AISummary from './ai-summary';
import TrackShipmentModal, { PackageFormData } from './track-shipment-modal';

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
        // Use DOMPurify for sanitization (ES6 import guarantees it's available)
        return DOMPurify.sanitize(html, emailSanitizeConfig);
    } catch (error) {
        console.error('Error sanitizing HTML with DOMPurify, using fallback:', error);

        // Fallback: basic sanitization when DOMPurify fails
        return html
            .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
            .replace(/\s*on\w+\s*=\s*["'][^"']*["']/gi, '')
            .replace(/javascript:/gi, '')
            // Only block non-image data URLs to allow legitimate inline images
            .replace(/data:(?!image\/)[^;]*;base64,[^"'\s]*/gi, '');
    }
};

interface EmailThreadCardProps {
    email: EmailMessage;
    isSelected?: boolean;
    onSelect?: (emailId: string) => void;
    showReadingPane?: boolean;
    inlineAvatar?: boolean;
    isFirstInThread?: boolean;
    threadId?: string;
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

// Utility function to get sender initials
const getSenderInitials = (name?: string, email?: string): string => {
    if (!name && !email) return '?';

    if (name) {
        // Clean the name: trim whitespace and handle multiple consecutive spaces
        const cleanName = name.trim().replace(/\s+/g, ' ');
        const parts = cleanName.split(' ');

        // Filter out empty parts and get first character of each part
        const initials = parts
            .filter(part => part.length > 0)
            .map(part => part[0])
            .join('');

        // For names with 2+ parts: use first and last initial
        if (parts.length >= 2) {
            return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
        }

        // For single names: use first 2 characters if available
        return initials.substring(0, 2).toUpperCase();
    }

    if (email) {
        // For email fallback: use first character of local part
        const localPart = email.split('@')[0];
        return localPart[0]?.toUpperCase() || '?';
    }

    return '?';
};

const EmailThreadCard: React.FC<EmailThreadCardProps> = ({
    email,
    isSelected = false,
    onSelect,
    inlineAvatar = false,
    isFirstInThread = false,
    threadId
}) => {
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isStarred, setIsStarred] = useState(false);
    const shipmentDetection = useShipmentDetection(email);

    const handleDownload = async () => {
        try {
            const testData = {
                provider: email.provider,
                date: email.date,
                subject: email.subject,
                sender: email.from_address?.email || '',
                body_data: {
                    contentType: email.body_html ? "HTML" : "Text",
                    content: email.body_html || email.body_text || ""
                }
            };

            const blob = new Blob([JSON.stringify(testData, null, 2)], {
                type: 'application/json'
            });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `email_test_${email.id}_${Date.now()}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

        } catch (error) {
            console.error('Failed to download email:', error);
            alert('Failed to download email. Please try again.');
        }
    };

    const handleTrackShipment = () => {
        setIsModalOpen(true);
    };

    const handleModalClose = () => {
        setIsModalOpen(false);
    };

    const handleTrackShipmentSubmit = async (packageData: PackageFormData) => {
        try {
            const packageDataWithEmail = {
                ...packageData,
                email_message_id: email.id,
            };

            const createdPackage = await shipmentsClient.createPackage(packageDataWithEmail);

            console.log('Package created successfully:', createdPackage);

            toast.success(`Successfully started tracking package ${packageData.tracking_number}`);

        } catch (error) {
            console.error('Failed to create package:', error);
            throw error;
        }
    };

    const handleStarToggle = () => {
        setIsStarred(!isStarred);
        // TODO: Implement actual star functionality
    };

    const handleReply = () => {
        // TODO: Implement reply functionality
        console.log('Reply to email:', email.id);
    };

    const handleArchive = () => {
        // TODO: Implement archive functionality
        console.log('Archive email:', email.id);
    };

    const handleSnooze = () => {
        // TODO: Implement snooze functionality
        console.log('Snooze email:', email.id);
    };

    const handleDelete = () => {
        // TODO: Implement delete functionality
        console.log('Delete email:', email.id);
    };

    const senderName = email.from_address?.name || email.from_address?.email || 'Unknown';
    const senderInitials = getSenderInitials(email.from_address?.name, email.from_address?.email);
    const formattedDate = formatEmailDate(email.date);
    const isUnread = !email.is_read;

    // Only handle expanded mode - tight mode is handled by email-thread.tsx
    return (
        <>
            <div
                className={`
                    group relative bg-white dark:bg-muted rounded-lg shadow-sm border p-4 mb-2 hover:shadow-md transition-shadow
                    ${isSelected ? 'ring-2 ring-blue-500' : ''}
                    ${isUnread ? 'bg-blue-50' : ''}
                `}
                onClick={() => onSelect?.(email.id)}
            >
                {/* Header Section - Avatar, Sender Info, Date, Actions */}
                <div className={`${inlineAvatar ? '' : 'flex items-start gap-3'} mb-3`}>
                    {/* Avatar - conditionally positioned */}
                    {!inlineAvatar && (
                        <div className="flex-shrink-0">
                            <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                                <span className="text-blue-600 font-medium text-sm">{senderInitials}</span>
                            </div>
                        </div>
                    )}

                    {/* Header Content */}
                    <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                    {/* Inline avatar with sender name */}
                                    {inlineAvatar && (
                                        <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                                            <span className="text-blue-600 font-medium text-xs">{senderInitials}</span>
                                        </div>
                                    )}
                                    <span className={`font-medium ${isUnread ? 'font-semibold' : ''}`}>
                                        {senderName}
                                    </span>
                                    {email.has_attachments && (
                                        <span className="text-gray-400">📎</span>
                                    )}
                                    {shipmentDetection.isShipmentEmail && (
                                        <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs">
                                            📦 Shipment
                                        </span>
                                    )}
                                </div>
                                <div className={`text-lg mb-2 ${isUnread ? 'font-semibold' : ''}`}>
                                    {email.subject || '(No subject)'}
                                </div>
                                <div className="text-sm text-gray-600">
                                    To: {email.to_addresses.map(addr => addr.name || addr.email).join(', ')}
                                </div>
                            </div>

                            {/* Date and actions */}
                            <div className="flex-shrink-0 flex flex-col items-end gap-2">
                                <span className="text-sm text-gray-500">{formattedDate}</span>

                                {/* Action buttons - always visible */}
                                <div className="flex items-center gap-1">
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-8 w-8 p-0"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleStarToggle();
                                        }}
                                        title="Star"
                                    >
                                        <Star className={`h-4 w-4 ${isStarred ? 'fill-current text-yellow-500' : ''}`} />
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-8 w-8 p-0"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleSnooze();
                                        }}
                                        title="Snooze"
                                    >
                                        <Clock className="h-4 w-4" />
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-8 w-8 p-0"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleDelete();
                                        }}
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
                                                onClick={(e) => e.stopPropagation()}
                                                title="More actions"
                                            >
                                                <MoreHorizontal className="h-4 w-4" />
                                            </Button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="end">
                                            <DropdownMenuItem onClick={(e) => {
                                                e.stopPropagation();
                                                handleReply();
                                            }}>
                                                <Reply className="h-4 w-4 mr-2" />
                                                Reply
                                            </DropdownMenuItem>
                                            <DropdownMenuItem onClick={(e) => {
                                                e.stopPropagation();
                                                handleArchive();
                                            }}>
                                                <Archive className="h-4 w-4 mr-2" />
                                                Archive
                                            </DropdownMenuItem>
                                            <DropdownMenuItem onClick={(e) => {
                                                e.stopPropagation();
                                                handleDownload();
                                            }}>
                                                <Download className="h-4 w-4 mr-2" />
                                                Download
                                            </DropdownMenuItem>
                                            {shipmentDetection.isShipmentEmail && (
                                                <DropdownMenuItem onClick={(e) => {
                                                    e.stopPropagation();
                                                    handleTrackShipment();
                                                }}>
                                                    <Wand2 className="h-4 w-4 mr-2" />
                                                    Track Shipment
                                                </DropdownMenuItem>
                                            )}
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Email Body Section - Full Width */}
                <div className="w-full">
                    {email.body_html ? (
                        <div
                            className="prose prose-sm max-w-none"
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
                            {email.snippet || email.body_text?.substring(0, 200) || 'No preview available'}
                        </div>
                    )}
                </div>

                {/* AI Summary Section */}
                <div className="mt-3">
                    <AISummary email={email} />
                </div>

                {/* Action buttons */}
                <div className="flex items-center gap-2 mt-3">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                            e.stopPropagation();
                            handleReply();
                        }}
                    >
                        <Reply className="h-4 w-4 mr-1" />
                        Reply
                    </Button>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                            e.stopPropagation();
                            handleArchive();
                        }}
                    >
                        <Archive className="h-4 w-4 mr-1" />
                        Archive
                    </Button>
                </div>
            </div>
            <TrackShipmentModal
                isOpen={isModalOpen}
                onClose={handleModalClose}
                email={email}
                onTrackShipment={handleTrackShipmentSubmit}
            />
        </>
    );
};

export default EmailThreadCard; 