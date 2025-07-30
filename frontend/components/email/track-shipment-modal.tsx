import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { useShipmentDataCollectionConsent } from '@/contexts/settings-context';
import { useShipmentDetection } from '@/hooks/use-shipment-detection';
import { DataCollectionRequest, shipmentsClient } from '@/lib/shipments-client';
import { EmailMessage } from '@/types/office-service';
import { CheckCircle, Info, Loader2, Package, Truck } from 'lucide-react';
import { useSession } from 'next-auth/react';
import React, { useEffect, useState } from 'react';

interface TrackShipmentModalProps {
    isOpen: boolean;
    onClose: () => void;
    email: EmailMessage;
    onTrackShipment: (packageData: PackageFormData) => Promise<void>;
}

export interface PackageFormData {
    tracking_number: string;
    carrier: string;
    status: string;
    recipient_name?: string;
    shipper_name?: string;
    package_description?: string;
    order_number?: string;
    tracking_link?: string;
}

const CARRIERS = [
    { value: 'amazon', label: 'Amazon' },
    { value: 'ups', label: 'UPS' },
    { value: 'fedex', label: 'FedEx' },
    { value: 'usps', label: 'USPS' },
    { value: 'dhl', label: 'DHL' },
    { value: 'unknown', label: 'Unknown' },
];

const STATUS_OPTIONS = [
    { value: 'pending', label: 'Pending' },
    { value: 'in_transit', label: 'In Transit' },
    { value: 'out_for_delivery', label: 'Out for Delivery' },
    { value: 'delivered', label: 'Delivered' },
    { value: 'exception', label: 'Exception' },
];

const TrackShipmentModal: React.FC<TrackShipmentModalProps> = ({
    isOpen,
    onClose,
    email,
    onTrackShipment
}) => {
    const { data: session } = useSession();
    const shipmentDetection = useShipmentDetection(email);
    const hasDataCollectionConsent = useShipmentDataCollectionConsent();
    const [isLoading, setIsLoading] = useState(false);
    const [isSuccess, setIsSuccess] = useState(false);
    const [formData, setFormData] = useState<PackageFormData>({
        tracking_number: '',
        carrier: 'unknown',
        status: 'pending',
        recipient_name: '',
        shipper_name: '',
        package_description: '',
        order_number: '',
        tracking_link: '',
    });
    const [initialFormData, setInitialFormData] = useState<PackageFormData | null>(null);

    // Initialize form with detected data when modal opens
    useEffect(() => {
        if (isOpen && shipmentDetection.isShipmentEmail) {
            const detectedData: PackageFormData = {
                tracking_number: shipmentDetection.trackingNumbers[0] || '',
                carrier: shipmentDetection.detectedCarrier || 'unknown',
                status: 'pending',
                recipient_name: '',
                shipper_name: '',
                package_description: email.subject || '',
                order_number: '',
                tracking_link: '',
            };
            setFormData(detectedData);
            setInitialFormData(detectedData);
        }
    }, [isOpen, shipmentDetection, email]);

    const handleInputChange = (field: keyof PackageFormData, value: string) => {
        setFormData(prev => ({
            ...prev,
            [field]: value
        }));
    };

    const submitDataCollection = async (packageData: PackageFormData) => {
        if (!hasDataCollectionConsent || !initialFormData || !session?.user?.id) {
            return;
        }

        try {
            // Check if user made any corrections
            const hasCorrections =
                packageData.tracking_number !== initialFormData.tracking_number ||
                packageData.carrier !== initialFormData.carrier ||
                packageData.status !== initialFormData.status ||
                packageData.order_number !== initialFormData.order_number ||
                packageData.package_description !== initialFormData.package_description;

            if (!hasCorrections) {
                return; // No corrections made, no need to collect data
            }

            const dataCollectionRequest: DataCollectionRequest = {
                user_id: session?.user?.id || '',
                email_message_id: email.id,
                original_email_data: {
                    subject: email.subject,
                    sender: email.from_address?.email,
                    body: email.body_html || email.body_text,
                },
                auto_detected_data: {
                    tracking_number: initialFormData.tracking_number,
                    carrier: initialFormData.carrier,
                    status: initialFormData.status,
                    order_number: initialFormData.order_number,
                    package_description: initialFormData.package_description,
                },
                user_corrected_data: {
                    tracking_number: packageData.tracking_number,
                    carrier: packageData.carrier,
                    status: packageData.status,
                    order_number: packageData.order_number,
                    package_description: packageData.package_description,
                },
                detection_confidence: shipmentDetection.confidence,
                correction_reason: hasCorrections ? 'User corrected auto-detected information' : undefined,
                consent_given: hasDataCollectionConsent,
            };

            console.log('Submitting data collection with user ID:', session?.user?.id);
            await shipmentsClient.collectData(dataCollectionRequest);
            console.log('Data collection submitted successfully');
        } catch (error) {
            console.error('Failed to submit data collection:', error);
            // Don't throw error - data collection failure shouldn't prevent tracking
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!formData.tracking_number.trim()) {
            alert('Tracking number is required');
            return;
        }

        setIsLoading(true);
        try {
            await onTrackShipment(formData);

            // Submit data collection if user has consented
            await submitDataCollection(formData);

            setIsSuccess(true);
            setTimeout(() => {
                onClose();
                setIsSuccess(false);
            }, 2000);
        } catch (error) {
            console.error('Failed to track shipment:', error);
            alert('Failed to track shipment. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleClose = () => {
        if (!isLoading) {
            onClose();
            setIsSuccess(false);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={handleClose}>
            <DialogContent className="sm:max-w-[95vw] max-h-[90vh] flex flex-col bg-white">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Package className="h-5 w-5" />
                        Track Shipment
                    </DialogTitle>
                </DialogHeader>

                <div className="flex-1 overflow-y-auto">
                    {isSuccess ? (
                        <div className="flex flex-col items-center justify-center py-8 text-center">
                            <CheckCircle className="h-12 w-12 text-green-500 mb-4" />
                            <h3 className="text-lg font-semibold mb-2">Shipment Tracked Successfully!</h3>
                            <p className="text-muted-foreground">
                                Your package is now being tracked. You'll receive updates on its status.
                            </p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* Email Content - Left Side */}
                            <div className="space-y-4">
                                <div className="border rounded-lg p-4">
                                    <h4 className="font-medium text-sm text-gray-700 mb-3">Email Content</h4>

                                    {/* Sender */}
                                    <div className="mb-3">
                                        <div className="text-xs font-medium text-gray-500 mb-1">From:</div>
                                        <div className="text-sm text-gray-900">
                                            {email.from_address?.name || email.from_address?.email || 'Unknown'}
                                        </div>
                                    </div>

                                    {/* Subject */}
                                    <div className="mb-3">
                                        <div className="text-xs font-medium text-gray-500 mb-1">Subject:</div>
                                        <div className="text-sm text-gray-900 font-medium">
                                            {email.subject || '(No subject)'}
                                        </div>
                                    </div>

                                    {/* Body */}
                                    <div>
                                        <div className="text-xs font-medium text-gray-500 mb-1">Body:</div>
                                        <div className="text-sm text-gray-900 max-h-48 overflow-y-auto border rounded p-3 bg-white">
                                            {email.body_text ? (
                                                <div className="whitespace-pre-wrap">
                                                    {email.body_text}
                                                </div>
                                            ) : email.body_html ? (
                                                <iframe
                                                    srcDoc={`
                                                        <!DOCTYPE html>
                                                        <html>
                                                        <head>
                                                            <meta charset="utf-8">
                                                            <style>
                                                                body {
                                                                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                                                    font-size: 14px;
                                                                    line-height: 1.5;
                                                                    color: #333;
                                                                    margin: 0;
                                                                    padding: 0;
                                                                    background: white;
                                                                }
                                                                * {
                                                                    box-sizing: border-box;
                                                                }
                                                            </style>
                                                        </head>
                                                        <body>
                                                            ${email.body_html}
                                                        </body>
                                                        </html>
                                                    `}
                                                    className="w-full h-full border-0"
                                                    style={{ minHeight: '200px' }}
                                                    sandbox="allow-same-origin"
                                                />
                                            ) : (
                                                <span className="text-gray-500 italic">No content</span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Form - Right Side */}
                            <div className="space-y-4">
                                <form onSubmit={handleSubmit} className="space-y-4">
                                    {/* Detection Status */}
                                    {shipmentDetection.isShipmentEmail && (
                                        <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                                            <div className="flex items-center gap-2 text-green-700">
                                                <CheckCircle className="h-4 w-4" />
                                                <span className="text-sm font-medium">
                                                    Shipment detected with {Math.round(shipmentDetection.confidence * 100)}% confidence
                                                </span>
                                            </div>
                                            {shipmentDetection.detectedCarrier && (
                                                <p className="text-sm text-green-600 mt-1">
                                                    Detected carrier: {shipmentDetection.detectedCarrier.toUpperCase()}
                                                </p>
                                            )}
                                        </div>
                                    )}

                                    {/* Data Collection Notice */}
                                    {hasDataCollectionConsent && (
                                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                                            <div className="flex items-start gap-2 text-blue-700">
                                                <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
                                                <div className="text-sm">
                                                    <p className="font-medium">Help Improve Detection</p>
                                                    <p className="text-blue-600 mt-1">
                                                        Your corrections help us improve our shipment detection accuracy.
                                                        Data is collected anonymously and securely.
                                                    </p>
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {/* Tracking Number */}
                                    <div className="space-y-2">
                                        <Label htmlFor="tracking_number">Tracking Number *</Label>
                                        <Input
                                            id="tracking_number"
                                            value={formData.tracking_number}
                                            onChange={(e) => handleInputChange('tracking_number', e.target.value)}
                                            placeholder="Enter tracking number"
                                            required
                                        />
                                    </div>

                                    {/* Carrier */}
                                    <div className="space-y-2">
                                        <Label htmlFor="carrier">Carrier</Label>
                                        <Select
                                            value={formData.carrier}
                                            onValueChange={(value) => handleInputChange('carrier', value)}
                                        >
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select carrier" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {CARRIERS.map((carrier) => (
                                                    <SelectItem key={carrier.value} value={carrier.value}>
                                                        {carrier.label}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    {/* Status */}
                                    <div className="space-y-2">
                                        <Label htmlFor="status">Status</Label>
                                        <Select
                                            value={formData.status}
                                            onValueChange={(value) => handleInputChange('status', value)}
                                        >
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select status" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {STATUS_OPTIONS.map((status) => (
                                                    <SelectItem key={status.value} value={status.value}>
                                                        {status.label}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    {/* Order Number */}
                                    <div className="space-y-2">
                                        <Label htmlFor="order_number">Order Number</Label>
                                        <Input
                                            id="order_number"
                                            value={formData.order_number}
                                            onChange={(e) => handleInputChange('order_number', e.target.value)}
                                            placeholder="Enter order number (optional)"
                                        />
                                    </div>

                                    {/* Package Description */}
                                    <div className="space-y-2">
                                        <Label htmlFor="package_description">Package Description</Label>
                                        <Textarea
                                            id="package_description"
                                            value={formData.package_description}
                                            onChange={(e) => handleInputChange('package_description', e.target.value)}
                                            placeholder="Enter package description (optional)"
                                            rows={2}
                                        />
                                    </div>

                                    {/* Recipient Name */}
                                    <div className="space-y-2">
                                        <Label htmlFor="recipient_name">Recipient Name</Label>
                                        <Input
                                            id="recipient_name"
                                            value={formData.recipient_name}
                                            onChange={(e) => handleInputChange('recipient_name', e.target.value)}
                                            placeholder="Enter recipient name (optional)"
                                        />
                                    </div>

                                    {/* Shipper Name */}
                                    <div className="space-y-2">
                                        <Label htmlFor="shipper_name">Shipper Name</Label>
                                        <Input
                                            id="shipper_name"
                                            value={formData.shipper_name}
                                            onChange={(e) => handleInputChange('shipper_name', e.target.value)}
                                            placeholder="Enter shipper name (optional)"
                                        />
                                    </div>

                                    {/* Tracking Link */}
                                    <div className="space-y-2">
                                        <Label htmlFor="tracking_link">Tracking Link</Label>
                                        <Input
                                            id="tracking_link"
                                            value={formData.tracking_link}
                                            onChange={(e) => handleInputChange('tracking_link', e.target.value)}
                                            placeholder="Enter tracking URL (optional)"
                                            type="url"
                                        />
                                    </div>
                                </form>
                            </div>
                        </div>
                    )}
                </div>

                <DialogFooter>
                    {!isSuccess && (
                        <>
                            <Button variant="outline" onClick={handleClose} disabled={isLoading}>
                                Cancel
                            </Button>
                            <Button
                                onClick={handleSubmit}
                                disabled={isLoading || !formData.tracking_number.trim()}
                                className="flex items-center gap-2"
                            >
                                {isLoading ? (
                                    <>
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                        Tracking...
                                    </>
                                ) : (
                                    <>
                                        <Truck className="h-4 w-4" />
                                        Track Shipment
                                    </>
                                )}
                            </Button>
                        </>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};

export default TrackShipmentModal; 