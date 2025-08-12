import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { useShipmentDetection } from '@/hooks/use-shipment-detection';
import { useShipmentEvents } from '@/hooks/use-shipment-events';
import { shipmentsClient } from '@/lib/shipments-client';
import { safeFormatDateAndTime } from '@/lib/utils';
import { EmailMessage } from '@/types/office-service';
import DOMPurify from 'dompurify';
import { Forward, MoreHorizontal, Package, PackageCheck, Reply, ReplyAll, Wand2 } from 'lucide-react';
import React, { useMemo, useState } from 'react';
import { toast } from 'sonner';
import AISummary from './ai-summary';
import TrackShipmentModal, { PackageFormData } from './track-shipment-modal';
import EmailThreadDraft from './email-thread-draft';
import { Draft } from '@/types/draft';
import { getSession } from 'next-auth/react';

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
    onReply?: (email: EmailMessage) => void;
    onReplyAll?: (email: EmailMessage) => void;
    onForward?: (email: EmailMessage) => void;
}

// Use the safe email date formatting function with detailed format
const formatEmailDate = (dateString: string): string => {
    return safeFormatDateAndTime(dateString, {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    }, {
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
    onReply,
    onReplyAll,
    onForward,
}) => {
    const [isModalOpen, setIsModalOpen] = useState(false);
    const shipmentDetection = useShipmentDetection(email);
    const { data: shipmentEvents, hasEvents } = useShipmentEvents(email.id);
    const [showInlineDraft, setShowInlineDraft] = useState(false);
    const [inlineDraft, setInlineDraft] = useState<Draft | null>(null);

    const buildInlineDraft = async (mode: 'reply' | 'reply_all' | 'forward') => {
        const session = await getSession();
        const userId = session?.user?.id || '';
        const toSet = new Set<string>();
        const ccSet = new Set<string>();
        const from = email.from_address?.email || '';
        const userEmail = session?.user?.email || '';
        if (mode === 'reply') {
            if (from) toSet.add(from);
        } else if (mode === 'reply_all') {
            if (from) toSet.add(from);
            email.to_addresses.forEach(a => { if (a.email && a.email !== userEmail) toSet.add(a.email); });
            email.cc_addresses.forEach(a => { if (a.email && a.email !== userEmail) ccSet.add(a.email); });
        }
        const subjectBase = email.subject || '';
        const subject = mode === 'forward'
            ? (subjectBase?.startsWith('Fwd:') ? subjectBase : `Fwd: ${subjectBase || ''}`)
            : (subjectBase?.startsWith('Re:') ? subjectBase : `Re: ${subjectBase || ''}`);
        const quotedBody = email.body_html || email.body_text || '';
        const bodyPrefix = mode === 'forward' ? '\n\n---------- Forwarded message ----------\n' : '\n\n';
        const content = `${bodyPrefix}${quotedBody}`;
        const newDraft: Draft = {
            id: `local_${Date.now()}`,
            type: 'email',
            status: 'draft',
            content,
            metadata: {
                subject: subject.trim(),
                recipients: Array.from(toSet),
                cc: Array.from(ccSet),
                bcc: [],
                provider: email.provider,
                replyToMessageId: email.provider_message_id,
            },
            isAIGenerated: false,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            userId,
            threadId: email.thread_id,
        };
        setInlineDraft(newDraft);
        setShowInlineDraft(true);
    };

    const handleReply = () => {
        onReply?.(email);
        buildInlineDraft('reply');
    };

    const handleReplyAll = () => {
        onReplyAll?.(email);
        buildInlineDraft('reply_all');
    };

    const handleForward = () => {
        onForward?.(email);
        buildInlineDraft('forward');
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
                                </div>
                                <div className="text-sm text-gray-600">
                                    To: {email.to_addresses.map(addr => addr.name || addr.email).join(', ')}
                                </div>
                            </div>

                            {/* Date, Shipment Icon, and Actions */}
                            <div className="flex items-center gap-2 flex-shrink-0">
                                <span className="text-sm text-gray-500">{formattedDate}</span>

                                {/* Shipment package icon */}
                                {(hasEvents ||
                                    shipmentDetection.trackingNumbers.length > 0 ||
                                    email.from_address?.email === 'shipment-tracking@amazon.com') && (
                                        <div className="relative group">
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                className="h-6 w-6 p-0 hover:bg-gray-100"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    handleTrackShipment();
                                                }}
                                                title={hasEvents
                                                    ? `${shipmentEvents.length} tracking event${shipmentEvents.length > 1 ? 's' : ''}`
                                                    : 'Track shipment'
                                                }
                                            >
                                                {hasEvents ? (
                                                    <PackageCheck
                                                        className="h-4 w-4 text-green-600"
                                                    />
                                                ) : (
                                                    <Package
                                                        className="h-4 w-4 text-gray-400"
                                                    />
                                                )}
                                            </Button>
                                        </div>
                                    )}

                                {/* 3-dot menu */}
                                <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            className="h-6 w-6 p-0"
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
                                            handleReplyAll();
                                        }}>
                                            <ReplyAll className="h-4 w-4 mr-2" />
                                            Reply All
                                        </DropdownMenuItem>
                                        <DropdownMenuItem onClick={(e) => {
                                            e.stopPropagation();
                                            handleForward();
                                        }}>
                                            <Forward className="h-4 w-4 mr-2" />
                                            Forward
                                        </DropdownMenuItem>
                                        <DropdownMenuItem onClick={(e) => {
                                            e.stopPropagation();
                                            handleTrackShipment();
                                        }}>
                                            <Wand2 className="h-4 w-4 mr-2" />
                                            Track Shipment
                                        </DropdownMenuItem>
                                    </DropdownMenuContent>
                                </DropdownMenu>
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

                {showInlineDraft && inlineDraft && (
                    <EmailThreadDraft
                        initialDraft={inlineDraft}
                        onClose={() => {
                            setShowInlineDraft(false);
                            setInlineDraft(null);
                        }}
                    />
                )}

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
                            handleReplyAll();
                        }}
                    >
                        <ReplyAll className="h-4 w-4 mr-1" />
                        Reply All
                    </Button>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                            e.stopPropagation();
                            handleForward();
                        }}
                    >
                        <Forward className="h-4 w-4 mr-1" />
                        Forward
                    </Button>
                </div>
            </div>

            {/* Track Shipment Modal */}
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