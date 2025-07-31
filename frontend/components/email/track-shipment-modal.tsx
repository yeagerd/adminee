import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { useShipmentDataCollectionConsent } from '@/contexts/settings-context';
import { useShipmentDetection } from '@/hooks/use-shipment-detection';
import { PACKAGE_STATUS, PACKAGE_STATUS_OPTIONS, PackageStatus } from '@/lib/package-status';
import { DataCollectionRequest, PackageResponse, shipmentsClient } from '@/lib/shipments-client';
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
    status: PackageStatus;
    recipient_name?: string;
    shipper_name?: string;
    package_description?: string;
    order_number?: string;
    tracking_link?: string;
    expected_delivery?: string;
}

const CARRIERS = [
    { value: 'amazon', label: 'Amazon' },
    { value: 'ups', label: 'UPS' },
    { value: 'fedex', label: 'FedEx' },
    { value: 'usps', label: 'USPS' },
    { value: 'dhl', label: 'DHL' },
    { value: 'unknown', label: 'Unknown' },
];

// Helper function to validate and safely convert status string to PackageStatus
const validatePackageStatus = (statusString: string): PackageStatus => {
    const validStatuses = PACKAGE_STATUS_OPTIONS.map(option => option.value);
    const upperCaseStatus = statusString.toUpperCase();

    // Check if the status is valid
    if (validStatuses.includes(upperCaseStatus as PackageStatus)) {
        return upperCaseStatus as PackageStatus;
    }

    // Log warning for invalid status
    console.warn(`Invalid package status received from backend: "${statusString}". Falling back to PENDING.`);

    // Return default status
    return PACKAGE_STATUS.PENDING;
};

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
    const [isParsing, setIsParsing] = useState(false);
    const [isCheckingPackage, setIsCheckingPackage] = useState(false);
    const [existingPackage, setExistingPackage] = useState<PackageResponse | null>(null);
    const [formData, setFormData] = useState<PackageFormData>({
        tracking_number: '',
        carrier: 'unknown',
        status: PACKAGE_STATUS.PENDING,
        recipient_name: '',
        shipper_name: '',
        package_description: '',
        order_number: '',
        tracking_link: '',
        expected_delivery: '',
    });
    const [initialFormData, setInitialFormData] = useState<PackageFormData | null>(null);

    // Check if a package already exists with the given tracking number and carrier
    const checkExistingPackage = async (trackingNumber: string, carrier?: string) => {
        if (!trackingNumber) {
            return;
        }

        setIsCheckingPackage(true);
        try {
            const existingPkg = await shipmentsClient.checkPackageExists(trackingNumber, carrier);
            setExistingPackage(existingPkg);

            // If existing package found, update form data with existing package info
            if (existingPkg) {
                setFormData(prev => ({
                    ...prev,
                    tracking_number: existingPkg.tracking_number,
                    carrier: existingPkg.carrier,
                    status: existingPkg.status,
                    recipient_name: existingPkg.recipient_name || '',
                    shipper_name: existingPkg.shipper_name || '',
                    package_description: existingPkg.package_description || '',
                    order_number: existingPkg.order_number || '',
                    tracking_link: existingPkg.tracking_link || '',
                    expected_delivery: existingPkg.estimated_delivery ?
                        new Date(existingPkg.estimated_delivery).toISOString().split('T')[0] : ''
                }));
            }
        } catch (error) {
            console.error('Failed to check for existing package:', error);
            if (error instanceof Error && error.message.includes('Multiple packages found')) {
                // Handle ambiguity - show error that carrier is required
                setExistingPackage(null);
            } else {
                setExistingPackage(null);
            }
        } finally {
            setIsCheckingPackage(false);
        }
    };

    // Parse email with backend when modal opens
    useEffect(() => {
        const parseEmailWithBackend = async () => {
            if (!isOpen) return;

            setIsParsing(true);
            try {
                // Call backend email parser
                const parseResponse = await shipmentsClient.parseEmail(email);

                if (parseResponse.is_shipment_email && parseResponse.suggested_package_data) {
                    const suggestedData = parseResponse.suggested_package_data;
                    const detectedData: PackageFormData = {
                        tracking_number: suggestedData.tracking_number || parseResponse.tracking_numbers[0]?.tracking_number || '',
                        carrier: suggestedData.carrier || parseResponse.detected_carrier || 'unknown',
                        status: suggestedData.status ? validatePackageStatus(suggestedData.status.toUpperCase()) : PACKAGE_STATUS.PENDING,
                        recipient_name: suggestedData.recipient_name || '',
                        shipper_name: suggestedData.shipper_name || '',
                        package_description: email.subject || '',
                        order_number: suggestedData.order_number || '',
                        tracking_link: suggestedData.tracking_link || '',
                        expected_delivery: suggestedData.estimated_delivery || '',
                    };
                    setFormData(detectedData);
                    setInitialFormData(detectedData);

                    // Check if package already exists
                    if (detectedData.tracking_number) {
                        const carrierToUse = detectedData.carrier !== 'unknown' ? detectedData.carrier : undefined;
                        await checkExistingPackage(detectedData.tracking_number, carrierToUse);
                    }
                } else if (shipmentDetection.isShipmentEmail) {
                    // Fallback to frontend detection if backend doesn't detect it
                    const detectedData: PackageFormData = {
                        tracking_number: shipmentDetection.trackingNumbers[0] || '',
                        carrier: shipmentDetection.detectedCarrier || 'unknown',
                        status: PACKAGE_STATUS.PENDING,
                        recipient_name: '',
                        shipper_name: '',
                        package_description: email.subject || '',
                        order_number: '',
                        tracking_link: '',
                        expected_delivery: '',
                    };
                    setFormData(detectedData);
                    setInitialFormData(detectedData);

                    // Check if package already exists
                    if (detectedData.tracking_number) {
                        const carrierToUse = detectedData.carrier !== 'unknown' ? detectedData.carrier : undefined;
                        await checkExistingPackage(detectedData.tracking_number, carrierToUse);
                    }
                }
            } catch (error) {
                console.error('Failed to parse email with backend:', error);
                // Fallback to frontend detection on error
                if (shipmentDetection.isShipmentEmail) {
                    const detectedData: PackageFormData = {
                        tracking_number: shipmentDetection.trackingNumbers[0] || '',
                        carrier: shipmentDetection.detectedCarrier || 'unknown',
                        status: PACKAGE_STATUS.PENDING,
                        recipient_name: '',
                        shipper_name: '',
                        package_description: email.subject || '',
                        order_number: '',
                        tracking_link: '',
                        expected_delivery: '',
                    };
                    setFormData(detectedData);
                    setInitialFormData(detectedData);

                    // Check if package already exists
                    if (detectedData.tracking_number) {
                        const carrierToUse = detectedData.carrier !== 'unknown' ? detectedData.carrier : undefined;
                        await checkExistingPackage(detectedData.tracking_number, carrierToUse);
                    }
                }
            } finally {
                setIsParsing(false);
            }
        };

        parseEmailWithBackend();
    }, [isOpen, email, shipmentDetection]);

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
            if (existingPackage) {
                // If package exists, create a tracking event instead of new package
                await shipmentsClient.createTrackingEvent(existingPackage.id, {
                    event_date: new Date().toISOString(),
                    status: formData.status,
                    location: undefined,
                    description: `New tracking event from email - Status: ${formData.status}`,
                });

                // Optionally update delivery date if provided
                if (formData.expected_delivery) {
                    await shipmentsClient.updatePackage(existingPackage.id, {
                        estimated_delivery: formData.expected_delivery,
                    });
                }
            } else {
                // Create new package
                await onTrackShipment(formData);
            }

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
                            <h3 className="text-lg font-semibold mb-2">
                                {existingPackage ? 'Tracking Event Added Successfully!' : 'Shipment Tracked Successfully!'}
                            </h3>
                            <p className="text-muted-foreground">
                                {existingPackage
                                    ? 'A new tracking event has been added to your existing package.'
                                    : 'Your package is now being tracked. You\'ll receive updates on its status.'
                                }
                            </p>
                        </div>
                    ) : isParsing ? (
                        <div className="flex flex-col items-center justify-center py-8 text-center">
                            <Loader2 className="h-12 w-12 text-blue-500 mb-4 animate-spin" />
                            <h3 className="text-lg font-semibold mb-2">Analyzing Email...</h3>
                            <p className="text-muted-foreground">
                                Extracting shipment information from your email.
                            </p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* Email Content - Left Side */}
                            <div className="flex flex-col h-full">
                                <div className="border rounded-lg p-4 flex flex-col h-full">
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
                                    <div className="flex-1 flex flex-col min-h-0">
                                        <div className="text-xs font-medium text-gray-500 mb-1">Body:</div>
                                        <div className="text-sm text-gray-900 flex-1 overflow-y-auto border rounded p-3 bg-white min-h-0">
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

                                    {/* Package Check Status */}
                                    {isCheckingPackage && (
                                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                                            <div className="flex items-center gap-2 text-blue-700">
                                                <Loader2 className="h-4 w-4 animate-spin" />
                                                <span className="text-sm font-medium">
                                                    Checking if package already exists...
                                                </span>
                                            </div>
                                        </div>
                                    )}

                                    {/* Existing Package Header */}
                                    {existingPackage && !isCheckingPackage && (
                                        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                                            <div className="flex items-center gap-3 mb-3">
                                                <CheckCircle className="h-5 w-5 text-green-600" />
                                                <div>
                                                    <h3 className="font-semibold text-green-800">Known Package</h3>
                                                    <p className="text-sm text-green-700">We'll add a new tracking event</p>
                                                </div>
                                            </div>

                                            {/* Tracking Number and Carrier */}
                                            <div className="grid grid-cols-2 gap-4 mb-4">
                                                <div>
                                                    <div className="text-xs font-medium text-green-700 mb-1">Tracking Number</div>
                                                    <div className="text-sm font-mono text-green-800 bg-green-100 px-2 py-1 rounded">
                                                        {existingPackage.tracking_number}
                                                    </div>
                                                </div>
                                                <div>
                                                    <div className="text-xs font-medium text-green-700 mb-1">Carrier</div>
                                                    <div className="text-sm font-medium text-green-800">
                                                        {existingPackage.carrier.toUpperCase()}
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Status and Expected Delivery */}
                                            <div className="grid grid-cols-2 gap-4">
                                                <div>
                                                    <div className="text-xs font-medium text-green-700 mb-1">Current Status</div>
                                                    <div className="text-sm font-medium text-green-800">
                                                        {existingPackage.status}
                                                    </div>
                                                </div>
                                                <div>
                                                    <div className="text-xs font-medium text-green-700 mb-1">Expected Delivery</div>
                                                    <div className="text-sm text-green-800">
                                                        {existingPackage.estimated_delivery ?
                                                            new Date(existingPackage.estimated_delivery).toLocaleDateString() :
                                                            'Not specified'
                                                        }
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {/* Existing Package Information */}
                                    {existingPackage && !isCheckingPackage && (
                                        <>
                                            {/* Divider */}
                                            <div className="border-t border-gray-200 my-6">
                                                <div className="bg-white px-3 -mt-3">
                                                    <span className="text-xs font-medium text-gray-500 bg-white px-2">Existing Package Information</span>
                                                </div>
                                            </div>

                                            {/* Existing Package Details */}
                                            <div className="space-y-4 bg-gray-50 rounded-lg p-4">
                                                <div className="grid grid-cols-1 gap-4">
                                                    {existingPackage.recipient_name && (
                                                        <div>
                                                            <div className="text-xs font-medium text-gray-600 mb-1">Recipient</div>
                                                            <div className="text-sm text-gray-900">{existingPackage.recipient_name}</div>
                                                        </div>
                                                    )}

                                                    {existingPackage.shipper_name && (
                                                        <div>
                                                            <div className="text-xs font-medium text-gray-600 mb-1">Shipper</div>
                                                            <div className="text-sm text-gray-900">{existingPackage.shipper_name}</div>
                                                        </div>
                                                    )}

                                                    {existingPackage.package_description && (
                                                        <div>
                                                            <div className="text-xs font-medium text-gray-600 mb-1">Description</div>
                                                            <div className="text-sm text-gray-900">{existingPackage.package_description}</div>
                                                        </div>
                                                    )}

                                                    {existingPackage.order_number && (
                                                        <div>
                                                            <div className="text-xs font-medium text-gray-600 mb-1">Order Number</div>
                                                            <div className="text-sm text-gray-900 font-mono">{existingPackage.order_number}</div>
                                                        </div>
                                                    )}

                                                    {existingPackage.tracking_link && (
                                                        <div>
                                                            <div className="text-xs font-medium text-gray-600 mb-1">Tracking Link</div>
                                                            <a
                                                                href={existingPackage.tracking_link}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                className="text-sm text-blue-600 hover:text-blue-800 underline"
                                                            >
                                                                View tracking
                                                            </a>
                                                        </div>
                                                    )}

                                                    <div>
                                                        <div className="text-xs font-medium text-gray-600 mb-1">Tracking Events</div>
                                                        <div className="text-sm text-gray-900">
                                                            {existingPackage.events_count} event{existingPackage.events_count !== 1 ? 's' : ''} recorded
                                                        </div>
                                                    </div>

                                                    <div>
                                                        <div className="text-xs font-medium text-gray-600 mb-1">Last Updated</div>
                                                        <div className="text-sm text-gray-900">
                                                            {new Date(existingPackage.updated_at).toLocaleString()}
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </>
                                    )}

                                    {/* New Tracking Event Information */}
                                    {existingPackage && !isCheckingPackage && (
                                        <>
                                            {/* Divider */}
                                            <div className="border-t border-gray-200 my-6">
                                                <div className="bg-white px-3 -mt-3">
                                                    <span className="text-xs font-medium text-gray-500 bg-white px-2">New Tracking Event</span>
                                                </div>
                                            </div>

                                            <div className="space-y-4">
                                                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                                    <div className="flex items-center gap-2 mb-3">
                                                        <Info className="h-4 w-4 text-blue-600" />
                                                        <span className="text-sm font-medium text-blue-800">Add a new tracking event</span>
                                                    </div>
                                                    <p className="text-sm text-blue-700">
                                                        You can add additional information about this tracking event, such as order number,
                                                        package description, or expected delivery date.
                                                    </p>
                                                </div>
                                            </div>
                                        </>
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
                                            disabled={!!existingPackage}
                                            className={existingPackage ? "bg-gray-100" : ""}
                                        />
                                    </div>

                                    {/* Carrier */}
                                    <div className="space-y-2">
                                        <Label htmlFor="carrier">Carrier</Label>
                                        <Select
                                            value={formData.carrier}
                                            onValueChange={(value) => handleInputChange('carrier', value)}
                                            disabled={!!existingPackage}
                                        >
                                            <SelectTrigger className={existingPackage ? "bg-gray-100" : ""}>
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
                                            disabled={!!existingPackage}
                                        >
                                            <SelectTrigger className={existingPackage ? "bg-gray-100" : ""}>
                                                <SelectValue placeholder="Select status" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {PACKAGE_STATUS_OPTIONS.map((status) => (
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

                                    {/* Expected Delivery */}
                                    <div className="space-y-2">
                                        <Label htmlFor="expected_delivery">Expected Delivery Date</Label>
                                        <Input
                                            id="expected_delivery"
                                            value={formData.expected_delivery}
                                            onChange={(e) => handleInputChange('expected_delivery', e.target.value)}
                                            placeholder="YYYY-MM-DD (optional)"
                                            type="date"
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
                                        {existingPackage ? 'Adding Event...' : 'Tracking...'}
                                    </>
                                ) : (
                                    <>
                                        <Truck className="h-4 w-4" />
                                        {existingPackage ? 'Add Tracking Event' : 'Track Shipment'}
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