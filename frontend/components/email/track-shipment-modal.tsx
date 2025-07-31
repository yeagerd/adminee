import FieldUpdateMessage from '@/components/general/field-update-message';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';

import { useShipmentDetection } from '@/hooks/use-shipment-detection';
import { PACKAGE_STATUS, PACKAGE_STATUS_OPTIONS, PackageStatus } from '@/lib/package-status';
import { DataCollectionRequest, PackageCreateRequest, PackageResponse, shipmentsClient } from '@/lib/shipments-client';
import { safeParseDateToISOString, safeParseDateToLocaleString } from '@/lib/utils';
import { EmailMessage } from '@/types/office-service';
import DOMPurify from 'dompurify';
import { CheckCircle, Info, Loader2, Package, Truck } from 'lucide-react';
import { useSession } from 'next-auth/react';
import React, { useEffect, useRef, useState } from 'react';

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

        // Fallback: comprehensive sanitization when DOMPurify fails
        return html
            // Remove script tags and their content
            .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
            // Remove event handler attributes
            .replace(/\s*on\w+\s*=\s*["'][^"']*["']/gi, '')
            // Remove javascript: protocol
            .replace(/javascript:/gi, '')
            // Remove all data URLs except legitimate image data URLs
            .replace(/data:(?!image\/)[^;]*;[^"'\s]*/gi, '')
            // Remove vbscript: protocol
            .replace(/vbscript:/gi, '')
            // Remove expression() CSS function (IE-specific XSS vector)
            .replace(/expression\s*\(/gi, '')
            // Remove eval() function calls
            .replace(/eval\s*\(/gi, '')
            // Remove iframe tags
            .replace(/<iframe[^>]*>[\s\S]*?<\/iframe>/gi, '')
            // Remove object tags
            .replace(/<object[^>]*>[\s\S]*?<\/object>/gi, '')
            // Remove embed tags
            .replace(/<embed[^>]*>/gi, '')
            // Remove applet tags
            .replace(/<applet[^>]*>[\s\S]*?<\/applet>/gi, '');
    }
};

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

// Helper function to get readable status label
const getReadableStatus = (status: PackageStatus): string => {
    const statusOption = PACKAGE_STATUS_OPTIONS.find(option => option.value === status);
    return statusOption ? statusOption.label : status;
};





const TrackShipmentModal: React.FC<TrackShipmentModalProps> = ({
    isOpen,
    onClose,
    email,
    onTrackShipment
}) => {
    const { data: session } = useSession();
    const shipmentDetection = useShipmentDetection(email);
    const [isLoading, setIsLoading] = useState(false);
    const [isSuccess, setIsSuccess] = useState(false);
    const [isParsing, setIsParsing] = useState(false);
    const [isCheckingPackage, setIsCheckingPackage] = useState(false);
    const [existingPackage, setExistingPackage] = useState<PackageResponse | null>(null);
    const [originalPackageData, setOriginalPackageData] = useState<PackageResponse | null>(null);
    const [dataCollectionConsent, setDataCollectionConsent] = useState(false);
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
    const debounceTimeoutRef = useRef<NodeJS.Timeout | null>(null);

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
                // Store the original package data for comparison
                setOriginalPackageData(existingPkg);

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
                    expected_delivery: safeParseDateToISOString(existingPkg.estimated_delivery)
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

    // Cleanup timeout on unmount or modal close
    useEffect(() => {
        return () => {
            if (debounceTimeoutRef.current) {
                clearTimeout(debounceTimeoutRef.current);
            }
        };
    }, []);

    const handleInputChange = (field: keyof PackageFormData, value: string) => {
        setFormData(prev => ({
            ...prev,
            [field]: value
        }));

        // If tracking number changed, check for existing package
        if (field === 'tracking_number' && value.trim()) {
            // Clear existing package when tracking number changes
            setExistingPackage(null);
            setOriginalPackageData(null);
            setIsCheckingPackage(true);

            // Clear any existing timeout to prevent race conditions
            if (debounceTimeoutRef.current) {
                clearTimeout(debounceTimeoutRef.current);
            }

            // Debounce the lookup to avoid too many API calls
            debounceTimeoutRef.current = setTimeout(async () => {
                try {
                    await checkExistingPackage(value.trim(), formData.carrier);
                } catch (error) {
                    console.error('Error checking existing package:', error);
                    setExistingPackage(null);
                } finally {
                    setIsCheckingPackage(false);
                }
            }, 500);
        }
    };

    const submitDataCollection = async (packageData: PackageFormData) => {
        if (!dataCollectionConsent || !initialFormData || !session?.user?.id) {
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
                consent_given: dataCollectionConsent,
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

                // Check if any package fields need to be updated
                const packageUpdates: Partial<PackageCreateRequest> = {};

                // Check each field and add to updates if different from original
                if (originalPackageData) {
                    if (formData.expected_delivery !== safeParseDateToISOString(originalPackageData.estimated_delivery)) {
                        packageUpdates.estimated_delivery = formData.expected_delivery;
                    }
                    if (formData.recipient_name !== (originalPackageData.recipient_name || '')) {
                        packageUpdates.recipient_name = formData.recipient_name;
                    }
                    if (formData.shipper_name !== (originalPackageData.shipper_name || '')) {
                        packageUpdates.shipper_name = formData.shipper_name;
                    }
                    if (formData.package_description !== (originalPackageData.package_description || '')) {
                        packageUpdates.package_description = formData.package_description;
                    }
                    if (formData.order_number !== (originalPackageData.order_number || '')) {
                        packageUpdates.order_number = formData.order_number;
                    }
                    if (formData.tracking_link !== (originalPackageData.tracking_link || '')) {
                        packageUpdates.tracking_link = formData.tracking_link;
                    }
                }

                // Update package if there are any changes
                if (Object.keys(packageUpdates).length > 0) {
                    await shipmentsClient.updatePackage(existingPackage.id, packageUpdates);
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
        // Clear any pending debounced operations
        if (debounceTimeoutRef.current) {
            clearTimeout(debounceTimeoutRef.current);
            debounceTimeoutRef.current = null;
        }

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
                                        <div className="text-sm text-gray-900 border rounded p-3 bg-white overflow-x-auto">
                                            {email.body_text ? (
                                                <div className="whitespace-pre-wrap min-w-0">
                                                    {email.body_text}
                                                </div>
                                            ) : email.body_html ? (
                                                <div
                                                    className="prose prose-sm max-w-none min-w-0"
                                                    style={{
                                                        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                                                        fontSize: '14px',
                                                        lineHeight: '1.5',
                                                        color: '#333',
                                                        overflowWrap: 'break-word',
                                                        wordWrap: 'break-word'
                                                    }}
                                                    dangerouslySetInnerHTML={{ __html: sanitizeEmailHtml(email.body_html) }}
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


                                    {/* Tracking Number */}
                                    <div className="flex items-center gap-3 p-1">
                                        <Label htmlFor="tracking_number" className="w-24 text-sm font-medium">Tracking Number</Label>
                                        <Input
                                            id="tracking_number"
                                            value={formData.tracking_number}
                                            onChange={(e) => handleInputChange('tracking_number', e.target.value)}
                                            placeholder="Enter tracking number"
                                            required
                                            className="flex-1"
                                        />
                                    </div>

                                    {/* Tracking Number Status */}
                                    {formData.tracking_number.trim() && (
                                        <div className="text-xs text-gray-600">
                                            {isCheckingPackage ? (
                                                <div className="flex items-center gap-1">
                                                    <Loader2 className="h-3 w-3 animate-spin" />
                                                    Searching...
                                                </div>
                                            ) : existingPackage ? (
                                                <div className="flex items-center gap-1 text-green-600">
                                                    <CheckCircle className="h-3 w-3" />
                                                    Existing package found.  Status: {getReadableStatus(existingPackage.status)}{existingPackage.estimated_delivery ? `.  Expected: ${safeParseDateToLocaleString(existingPackage.estimated_delivery)}` : ''}
                                                </div>
                                            ) : (
                                                <div className="flex items-center gap-1 text-blue-600">
                                                    <Info className="h-3 w-3" />
                                                    New package
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* Carrier */}
                                    <div className="flex items-center gap-3 p-1">
                                        <Label htmlFor="carrier" className="w-24 text-sm font-medium">Carrier</Label>
                                        <Select
                                            value={formData.carrier}
                                            onValueChange={(value) => handleInputChange('carrier', value)}
                                        >
                                            <SelectTrigger className="flex-1">
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
                                    <div className="flex items-center gap-3 p-1">
                                        <Label htmlFor="status" className="w-24 text-sm font-medium">Status</Label>
                                        <Select
                                            value={formData.status}
                                            onValueChange={(value) => handleInputChange('status', value)}
                                        >
                                            <SelectTrigger className="flex-1">
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

                                    {/* Expected Delivery */}
                                    <div className="flex items-center gap-3 p-1">
                                        <Label htmlFor="expected_delivery" className="w-24 text-sm font-medium">Expected Delivery</Label>
                                        <Input
                                            id="expected_delivery"
                                            value={formData.expected_delivery}
                                            onChange={(e) => handleInputChange('expected_delivery', e.target.value)}
                                            placeholder="YYYY-MM-DD (optional)"
                                            type="date"
                                            className="flex-1"
                                        />
                                    </div>

                                    {/* Separator for existing packages */}
                                    {existingPackage && (
                                        <div className="border-t-2 border-gray-300 my-4"></div>
                                    )}

                                    {/* Order Number */}
                                    <div className="flex items-center gap-3 p-1">
                                        <Label htmlFor="order_number" className="w-24 text-sm font-medium">Order Number</Label>
                                        <Input
                                            id="order_number"
                                            value={formData.order_number}
                                            onChange={(e) => handleInputChange('order_number', e.target.value)}
                                            placeholder="Enter order number (optional)"
                                            className="flex-1"
                                        />
                                    </div>
                                    {existingPackage && formData.order_number && (
                                        <FieldUpdateMessage
                                            existingPackage={existingPackage}
                                            currentValue={formData.order_number}
                                            originalValue={originalPackageData?.order_number}
                                        />
                                    )}

                                    {/* Package Description */}
                                    <div className="flex items-start gap-3 p-1">
                                        <Label htmlFor="package_description" className="w-24 text-sm font-medium mt-2">Description</Label>
                                        <Textarea
                                            id="package_description"
                                            value={formData.package_description}
                                            onChange={(e) => handleInputChange('package_description', e.target.value)}
                                            placeholder="Enter package description (optional)"
                                            rows={2}
                                            className="flex-1"
                                        />
                                    </div>
                                    {existingPackage && formData.package_description && (
                                        <FieldUpdateMessage
                                            existingPackage={existingPackage}
                                            currentValue={formData.package_description}
                                            originalValue={originalPackageData?.package_description}
                                        />
                                    )}

                                    {/* Recipient Name */}
                                    <div className="flex items-center gap-3 p-1">
                                        <Label htmlFor="recipient_name" className="w-24 text-sm font-medium">Recipient</Label>
                                        <Input
                                            id="recipient_name"
                                            value={formData.recipient_name}
                                            onChange={(e) => handleInputChange('recipient_name', e.target.value)}
                                            placeholder="Enter recipient name (optional)"
                                            className="flex-1"
                                        />
                                    </div>
                                    {existingPackage && formData.recipient_name && (
                                        <FieldUpdateMessage
                                            existingPackage={existingPackage}
                                            currentValue={formData.recipient_name}
                                            originalValue={originalPackageData?.recipient_name}
                                        />
                                    )}

                                    {/* Shipper Name */}
                                    <div className="flex items-center gap-3 p-1">
                                        <Label htmlFor="shipper_name" className="w-24 text-sm font-medium">Shipper</Label>
                                        <Input
                                            id="shipper_name"
                                            value={formData.shipper_name}
                                            onChange={(e) => handleInputChange('shipper_name', e.target.value)}
                                            placeholder="Enter shipper name (optional)"
                                            className="flex-1"
                                        />
                                    </div>
                                    {existingPackage && formData.shipper_name && (
                                        <FieldUpdateMessage
                                            existingPackage={existingPackage}
                                            currentValue={formData.shipper_name}
                                            originalValue={originalPackageData?.shipper_name}
                                        />
                                    )}

                                    {/* Tracking Link */}
                                    <div className="flex items-center gap-3 p-1">
                                        <Label htmlFor="tracking_link" className="w-24 text-sm font-medium">Tracking Link</Label>
                                        <Input
                                            id="tracking_link"
                                            value={formData.tracking_link}
                                            onChange={(e) => handleInputChange('tracking_link', e.target.value)}
                                            placeholder="Enter tracking URL (optional)"
                                            type="url"
                                            className="flex-1"
                                        />
                                    </div>
                                    {existingPackage && formData.tracking_link && (
                                        <FieldUpdateMessage
                                            existingPackage={existingPackage}
                                            currentValue={formData.tracking_link}
                                            originalValue={originalPackageData?.tracking_link}
                                        />
                                    )}

                                    {/* Data Collection Consent */}
                                    <div className="flex items-start space-x-2">
                                        <Checkbox
                                            id="data_collection_consent"
                                            checked={dataCollectionConsent}
                                            onCheckedChange={(checked) => setDataCollectionConsent(checked as boolean)}
                                        />
                                        <div className="grid gap-1.5 leading-none">
                                            <Label
                                                htmlFor="data_collection_consent"
                                                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                                            >
                                                Use my data to improve the service
                                            </Label>
                                            <p className="text-sm text-muted-foreground">
                                                Your corrections help us improve our shipment detection accuracy.
                                                Data is collected anonymously and securely.
                                            </p>
                                        </div>
                                    </div>
                                </form >
                            </div >
                        </div >
                    )}
                </div >

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
            </DialogContent >
        </Dialog >
    );
};

export default TrackShipmentModal; 