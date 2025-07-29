import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { EmailMessage } from '@/types/office-service';
import { Download, Wand2, ChevronDown } from 'lucide-react';
import React, { useState } from 'react';
import AISummary from './ai-summary';
import { useShipmentDetection } from '@/hooks/use-shipment-detection';

interface EmailCardProps {
    email: EmailMessage;
}

const EmailCard: React.FC<EmailCardProps> = ({ email }) => {
    const [isDownloading, setIsDownloading] = useState(false);
    const shipmentDetection = useShipmentDetection(email);

    const handleDownload = async () => {
        setIsDownloading(true);
        try {
            // Create a test data object that mimics the API format
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

            // Create and download the file
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
        // TODO: Implement shipment tracking modal
        console.log('Track shipment clicked for email:', email.id);
        console.log('Shipment detection result:', shipmentDetection);
    };

    // Placeholder logic for flags (customize as needed)
    // const isHighPriority = email.labels?.includes('important');
    // const hasCalendarEvent = false; // Not available in EmailMessage
    // const hasPackageTracking = false; // Not available in EmailMessage

    return (
        <div className="bg-white dark:bg-muted rounded-lg shadow p-4 mb-2 border">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    {/* {isHighPriority && <span className="text-red-500 font-bold">! </span>} */}
                    <span className="font-medium">{email.subject || '(No subject)'}</span>
                    {shipmentDetection.isShipmentEmail && (
                        <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs">
                            📦 Shipment
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">{new Date(email.date).toLocaleString()}</span>
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0"
                                title="Email actions"
                                aria-label="Email actions menu"
                            >
                                <Wand2 className="h-4 w-4" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                            <DropdownMenuItem 
                                onClick={handleDownload}
                                disabled={isDownloading}
                                className="flex items-center gap-2"
                            >
                                <Download className="h-4 w-4" />
                                {isDownloading ? 'Downloading...' : 'Download Email'}
                            </DropdownMenuItem>
                            <DropdownMenuItem 
                                onClick={handleTrackShipment}
                                className={`flex items-center gap-2 ${
                                    shipmentDetection.isShipmentEmail 
                                        ? 'text-green-600 font-medium' 
                                        : ''
                                }`}
                            >
                                <Wand2 className="h-4 w-4" />
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
            <div className="mt-1 text-sm text-muted-foreground">From: {email.from_address?.name || email.from_address?.email || 'Unknown'}</div>
            <div className="mt-1 text-sm text-muted-foreground">To: {email.to_addresses.map(addr => addr.name || addr.email).join(', ')}</div>
            {/* <div className="mt-2">
                {hasCalendarEvent && <span className="mr-2 px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">Calendar</span>}
                {hasPackageTracking && <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs">Package</span>}
            </div> */}
            <div className="mt-2">
                <AISummary email={email} />
            </div>
            <div className="mt-2 flex gap-2">
                <button className="text-primary underline text-sm">Reply</button>
                {/* This should open the draft pane with a reply draft */}
            </div>
        </div>
    );
};

export default EmailCard; 