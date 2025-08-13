import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { useShipmentDetection } from '@/hooks/use-shipment-detection';
import { useShipmentEvents } from '@/hooks/use-shipment-events';
import { shipmentsClient } from '@/lib/shipments-client';
import { safeFormatDateAndTime } from '@/lib/utils';
import { EmailMessage } from '@/types/office-service';
import DOMPurify from 'dompurify';
import { Forward, MoreHorizontal, Package, PackageCheck, Reply, ReplyAll, Wand2 } from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import AISummary from './ai-summary';
import TrackShipmentModal, { PackageFormData } from './track-shipment-modal';
// inline draft removed; thread-level draft card is handled by parent

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

// Heuristic splitter for previous/quoted content in email HTML/text
function splitQuotedContent({ html, text }: { html?: string; text?: string }): { visibleHtml?: string; quotedHtml?: string; visibleText?: string; quotedText?: string } | null {
    // Prefer HTML splitting when available; fall back to text-only heuristics
    if (typeof window !== 'undefined' && html && html.trim()) {
        const sanitized = sanitizeEmailHtml(html);
        const container = document.createElement('div');
        container.innerHTML = sanitized;

        // First try common provider-specific markers
        const quoteSelectors = [
            '.gmail_quote',
            'blockquote.gmail_quote',
            'blockquote[type="cite"]',
            'div.yahoo_quoted',
            'div[id^="yiv"] blockquote',
            'div[id^="yui_"] blockquote',
        ];

        let quoteNode: Element | null = null;
        for (const sel of quoteSelectors) {
            const found = container.querySelector(sel);
            if (found) { quoteNode = found as Element; break; }
        }

        // Consider a horizontal rule as a common boundary between new and quoted content
        if (!quoteNode) {
            const hrBoundary = container.querySelector('hr');
            if (hrBoundary) {
                quoteNode = hrBoundary as Element;
            }
        }

        // If not found, search for textual markers within the DOM
        if (!quoteNode) {
            const textContent = container.textContent || '';
            const patterns: RegExp[] = [
                /-{5,}\s*Original Message\s*-{5,}/i,
                /Begin forwarded message:/i,
                /Forwarded message:/i,
                /On .{0,200}?wrote:/i,
                // Pattern for Outlook-style quoted headers
                // Look for From: followed by Sent: and To: in sequence (indicating quoted content)
                // Use a more flexible approach that doesn't rely on exact newline positioning
                /From:\s[^<]+Sent:\s[^<]+To:\s[^<]+/i,
            ];
            let matchIndex = -1;
            for (const re of patterns) {
                const m = textContent.match(re);
                if (m && typeof m.index === 'number') { matchIndex = m.index; break; }
            }
            if (matchIndex >= 0) {
                // Locate the text node containing the match index
                const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
                let cum = 0;
                let textNode: Text | null = null;
                while (walker.nextNode()) {
                    const node = walker.currentNode as Text;
                    const len = node.textContent?.length || 0;
                    if (cum + len > matchIndex) { textNode = node; break; }
                    cum += len;
                }
                quoteNode = textNode?.parentElement || null;
            }
        }

        // If still not found, look for a separator line (dashes/underscores) as a block
        if (!quoteNode) {
            const candidates = Array.from(container.querySelectorAll('p, div, span, pre, td, li')) as Element[];
            for (const el of candidates) {
                const t = (el.textContent || '').trim();
                if (/^[-_=*]{5,}$/.test(t)) { quoteNode = el; break; }
            }
        }

        if (!quoteNode) {
            return null;
        }

        // Helper: compute path from container to quoteNode to re-find in clones
        const computePath = (node: Element): number[] => {
            const path: number[] = [];
            let cur: Element | null = node;
            while (cur && cur !== container) {
                const parentEl: Element | null = cur.parentElement;
                if (!parentEl) break;
                const idx = Array.prototype.indexOf.call(parentEl.childNodes, cur);
                path.unshift(idx);
                cur = parentEl;
            }
            return path;
        };

        const findByPath = (root: Element, path: number[]): Node | null => {
            let cur: Node = root;
            for (const idx of path) {
                if (!cur.childNodes || !cur.childNodes[idx]) return null;
                cur = cur.childNodes[idx];
            }
            return cur;
        };

        const pathToQuote = computePath(quoteNode);

        // Build visible part: remove everything from the boundary to the end using a DOM Range
        const visibleContainer = container.cloneNode(true) as HTMLElement;
        const q1 = findByPath(visibleContainer, pathToQuote);
        if (q1) {
            const range = document.createRange();
            range.setStartBefore(q1);
            // If there is no lastChild, the container is empty; otherwise remove to the end
            const last = visibleContainer.lastChild;
            if (last) {
                range.setEndAfter(last);
                range.deleteContents();
            }
        }

        // Build quoted part: remove everything before the boundary using a DOM Range
        const quotedContainer = container.cloneNode(true) as HTMLElement;
        const q2 = findByPath(quotedContainer, pathToQuote);
        if (q2) {
            const range2 = document.createRange();
            const first = quotedContainer.firstChild;
            if (first) {
                range2.setStartBefore(first);
                range2.setEndBefore(q2);
                range2.deleteContents();
            }
        }

        const visibleHtml = visibleContainer.innerHTML.trim();
        const quotedHtml = quotedContainer.innerHTML.trim();

        // Avoid degenerate splits where visible is empty or identical to original
        if (!quotedHtml || quotedHtml.length < 20) {
            return null;
        }
        // If the visible part is empty or whitespace-only, treat as unsplittable
        const visibleStripped = visibleHtml.replace(/&nbsp;|\s+/g, '');
        if (!visibleStripped) {
            return null;
        }
        return { visibleHtml, quotedHtml };
    }

    // Text-only fallback splitter
    if (text && text.trim()) {
        const src = text;
        const patterns: RegExp[] = [
            /\n-{5,}\s*Original Message\s*-{5,}\n/i,
            /\nBegin forwarded message:\n/i,
            /\nForwarded message:\n/i,
            /\nOn .{0,200}?wrote:\n/i,
            // Pattern for Outlook-style quoted headers
            // Look for From: followed by Sent: and To: in sequence (indicating quoted content)
            // Use a more flexible approach that doesn't rely on exact newline positioning
            /From:\s.+\s+Sent:\s.+\s+To:\s.+/i,
            /\n[-_=*]{5,}\n/, // separator line
        ];
        let idx = -1;
        for (const re of patterns) {
            const m = src.match(re);
            if (m && typeof m.index === 'number') { idx = m.index; break; }
        }
        if (idx >= 0) {
            return {
                visibleText: src.slice(0, idx).trimEnd(),
                quotedText: src.slice(idx).trimStart(),
            };
        }
    }

    return null;
}

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
    // inline draft removed; thread-level draft card will be shown by parent

    const [showQuoted, setShowQuoted] = useState(false);
    const [splitResult, setSplitResult] = useState<{ visibleHtml?: string; quotedHtml?: string; visibleText?: string; quotedText?: string } | null>(null);

    // Compute quoted split on client to avoid SSR document usage
    useEffect(() => {
        const res = splitQuotedContent({ html: email.body_html, text: email.body_text });
        setSplitResult(res);
        // If the entire message is detected as quoted (no visible part), show quoted by default
        const shouldShowQuotedHtml = !!email.body_html && !res?.visibleHtml && !!res?.quotedHtml;
        const shouldShowQuotedText = !email.body_html && !res?.visibleText && !!res?.quotedText;
        setShowQuoted(shouldShowQuotedHtml || shouldShowQuotedText);
    }, [email.body_html, email.body_text]);

    const sanitizedHtml = useMemo(() => (email.body_html ? sanitizeEmailHtml(email.body_html) : ''), [email.body_html]);

    const handleReply = () => {
        onReply?.(email);
    };

    const handleReplyAll = () => {
        onReplyAll?.(email);
    };

    const handleForward = () => {
        onForward?.(email);
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
                        splitResult?.visibleHtml || splitResult?.quotedHtml ? (
                            // If there is only quoted content and no visible content, render quoted directly without toggle
                            !splitResult?.visibleHtml && splitResult?.quotedHtml ? (
                                <div className="mt-2 border rounded bg-gray-50 p-3">
                                    <div
                                        className="prose prose-sm max-w-none"
                                        dangerouslySetInnerHTML={{ __html: splitResult.quotedHtml }}
                                    />
                                </div>
                            ) : (
                                <>
                                    {/* Visible (new) content */}
                                    {splitResult.visibleHtml && (
                                        <div
                                            className="prose prose-sm max-w-none"
                                            style={{
                                                fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                                                fontSize: '14px',
                                                lineHeight: '1.5',
                                                color: '#333'
                                            }}
                                            dangerouslySetInnerHTML={{ __html: splitResult.visibleHtml }}
                                        />
                                    )}
                                    {/* Toggle for quoted part */}
                                    {splitResult.quotedHtml && (
                                        <div className="mt-2">
                                            <button
                                                className="text-sm text-blue-600 hover:underline"
                                                onClick={(e) => { e.stopPropagation(); setShowQuoted((s) => !s); }}
                                                type="button"
                                            >
                                                {showQuoted ? 'Hide quoted text' : 'Show quoted text'}
                                            </button>
                                            {showQuoted && (
                                                <div className="mt-2 border rounded bg-gray-50 p-3">
                                                    <div
                                                        className="prose prose-sm max-w-none"
                                                        dangerouslySetInnerHTML={{ __html: splitResult.quotedHtml }}
                                                    />
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </>
                            )
                        ) : (
                            <div
                                className="prose prose-sm max-w-none"
                                style={{
                                    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                                    fontSize: '14px',
                                    lineHeight: '1.5',
                                    color: '#333'
                                }}
                                dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
                            />
                        )
                    ) : (
                        // Plain text fallback
                        splitResult?.visibleText || splitResult?.quotedText ? (
                            // If there is only quoted text and no visible text, render quoted directly without toggle
                            !splitResult?.visibleText && splitResult?.quotedText ? (
                                <div className="mt-2 border rounded bg-gray-50 p-3">
                                    <pre className="text-xs text-gray-700 whitespace-pre-wrap">{splitResult.quotedText}</pre>
                                </div>
                            ) : (
                                <div className="text-sm text-gray-700">
                                    {splitResult.visibleText && (
                                        <pre className="whitespace-pre-wrap font-sans text-[14px] leading-5 text-gray-800">{splitResult.visibleText}</pre>
                                    )}
                                    {splitResult.quotedText && (
                                        <div className="mt-2">
                                            <button
                                                className="text-sm text-blue-600 hover:underline"
                                                onClick={(e) => { e.stopPropagation(); setShowQuoted((s) => !s); }}
                                                type="button"
                                            >
                                                {showQuoted ? 'Hide quoted text' : 'Show quoted text'}
                                            </button>
                                            {showQuoted && (
                                                <div className="mt-2 border rounded bg-gray-50 p-3">
                                                    <pre className="text-xs text-gray-700 whitespace-pre-wrap">{splitResult.quotedText}</pre>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )
                        ) : (
                            <div className="text-sm text-gray-700">
                                {email.snippet || email.body_text?.substring(0, 200) || 'No preview available'}
                            </div>
                        )
                    )}
                </div>

                {/* AI Summary Section */}
                <div className="mt-3">
                    <AISummary email={email} />
                </div>

                {/* Inline draft removed; thread-level draft card will be shown by parent */}

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