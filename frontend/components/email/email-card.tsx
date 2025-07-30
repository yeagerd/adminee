import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { toast } from '@/components/ui/use-toast';
import { useShipmentDetection } from '@/hooks/use-shipment-detection';
import { shipmentsClient } from '@/lib/shipments-client';
import { EmailMessage } from '@/types/office-service';
import { Archive, Clock, Download, MoreHorizontal, Reply, Star, Trash2, Wand2 } from 'lucide-react';
import React, { useState } from 'react';
import AISummary from './ai-summary';
import TrackShipmentModal, { PackageFormData } from './track-shipment-modal';

interface EmailCardProps {
    email: EmailMessage;
    mode: 'tight' | 'expanded';
    isSelected?: boolean;
    onSelect?: (emailId: string) => void;
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

// Utility function to get sender initials
const getSenderInitials = (name?: string, email?: string): string => {
    if (name) {
        const parts = name.split(' ');
        if (parts.length >= 2) {
            return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
        }
        return name[0]?.toUpperCase() || '?';
    }
    if (email) {
        return email[0]?.toUpperCase() || '?';
    }
    return '?';
};

const EmailCard: React.FC<EmailCardProps> = ({
    email,
    mode,
    isSelected = false,
    onSelect,
    showReadingPane = false
}) => {
    const [isDownloading, setIsDownloading] = useState(false);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isStarred, setIsStarred] = useState(false);
    const shipmentDetection = useShipmentDetection(email);

    const handleDownload = async () => {
        setIsDownloading(true);
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
        } finally {
            setIsDownloading(false);
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

            toast({
                title: "Shipment Tracked",
                description: `Successfully started tracking package ${packageData.tracking_number}`,
            });

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

    if (mode === 'tight') {
        return (
            <>
                <div
                    className={`
                        group relative flex items-center gap-3 px-4 py-2 border-b border-gray-100 hover:bg-gray-50 cursor-pointer
                        ${isSelected ? 'bg-blue-50 border-l-4 border-l-blue-500' : ''}
                        ${isUnread ? 'bg-blue-50 font-semibold' : ''}
                    `}
                    onClick={() => onSelect?.(email.id)}
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
                            handleStarToggle();
                        }}
                        className={`p-1 rounded hover:bg-gray-200 ${isStarred ? 'text-yellow-500' : 'text-gray-400'}`}
                    >
                        <Star className={`w-4 h-4 ${isStarred ? 'fill-current' : ''}`} />
                    </button>

                    {/* Sender */}
                    <div className="flex-shrink-0 w-32">
                        <span className={`truncate ${isUnread ? 'font-semibold' : ''}`}>
                            {senderName}
                        </span>
                    </div>

                    {/* Subject and snippet */}
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                            <span className={`truncate ${isUnread ? 'font-semibold' : ''}`}>
                                {email.subject || '(No subject)'}
                            </span>
                            {email.has_attachments && (
                                <span className="text-gray-400">📎</span>
                            )}
                            {shipmentDetection.isShipmentEmail && (
                                <span className="text-green-600">📦</span>
                            )}
                        </div>
                        <div className="text-sm text-gray-500 truncate">
                            {email.snippet || email.body_text?.substring(0, 100) || ''}
                        </div>
                    </div>

                    {/* Date */}
                    <div className="flex-shrink-0 w-16 text-right">
                        <span className="text-sm text-gray-500">{formattedDate}</span>
                    </div>

                    {/* Hover actions */}
                    <div className="absolute right-2 top-1/2 transform -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0 hover:bg-gray-200"
                            onClick={(e) => {
                                e.stopPropagation();
                                handleArchive();
                            }}
                            title="Archive"
                        >
                            <Archive className="h-4 w-4" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0 hover:bg-gray-200"
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
                            className="h-8 w-8 p-0 hover:bg-gray-200"
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
                                    className="h-8 w-8 p-0 hover:bg-gray-200"
                                    onClick={(e) => e.stopPropagation()}
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
                                <DropdownMenuItem onClick={handleDownload} disabled={isDownloading}>
                                    <Download className="h-4 w-4 mr-2" />
                                    {isDownloading ? 'Downloading...' : 'Download Email'}
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                    onClick={handleTrackShipment}
                                    className={shipmentDetection.isShipmentEmail ? 'text-green-600 font-medium' : ''}
                                >
                                    <Wand2 className="h-4 w-4 mr-2" />
                                    Track Shipment
                                    {shipmentDetection.isShipmentEmail && (
                                        <span className="ml-auto text-xs bg-green-100 text-green-700 px-1 rounded">
                                            {shipmentDetection.detectedCarrier || 'Detected'}
                                        </span>
                                    )}
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
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
    }

    // Expanded mode
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
                <div className="flex items-start gap-3">
                    {/* Avatar */}
                    <div className="flex-shrink-0">
                        <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                            <span className="text-blue-600 font-medium text-sm">{senderInitials}</span>
                        </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between">
                            <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
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
                                <div className="text-sm text-gray-600 mb-3">
                                    To: {email.to_addresses.map(addr => addr.name || addr.email).join(', ')}
                                </div>
                                <div className="text-sm text-gray-700 mb-3">
                                    {email.snippet || email.body_text?.substring(0, 200) || 'No preview available'}
                                </div>

                                {/* AI Summary */}
                                <div className="mb-3">
                                    <AISummary email={email} />
                                </div>

                                {/* Action buttons */}
                                <div className="flex items-center gap-2">
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

                            {/* Date and actions */}
                            <div className="flex-shrink-0 flex flex-col items-end gap-2">
                                <span className="text-sm text-gray-500">{formattedDate}</span>

                                {/* Hover actions */}
                                <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
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
                                            <DropdownMenuItem onClick={handleDownload} disabled={isDownloading}>
                                                <Download className="h-4 w-4 mr-2" />
                                                {isDownloading ? 'Downloading...' : 'Download Email'}
                                            </DropdownMenuItem>
                                            <DropdownMenuItem
                                                onClick={handleTrackShipment}
                                                className={shipmentDetection.isShipmentEmail ? 'text-green-600 font-medium' : ''}
                                            >
                                                <Wand2 className="h-4 w-4 mr-2" />
                                                Track Shipment
                                                {shipmentDetection.isShipmentEmail && (
                                                    <span className="ml-auto text-xs bg-green-100 text-green-700 px-1 rounded">
                                                        {shipmentDetection.detectedCarrier || 'Detected'}
                                                    </span>
                                                )}
                                            </DropdownMenuItem>
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                </div>
                            </div>
                        </div>
                    </div>
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

export default EmailCard; 