import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import FieldUpdateMessage from '@/components/ui/field-update-message';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { PACKAGE_STATUS_OPTIONS, PackageStatus } from '@/lib/package-status';
import { PackageResponse } from '@/api/clients/shipments-client';
import { ShipmentsClient } from '@/api/clients/shipments-client';
import { safeParseDateToISOString, safeParseDateToLocaleString } from '@/lib/utils';
import { BadgeCheck, Calendar, ExternalLink, FileText, Hash, Loader2, Package, Tag, Trash2, Truck, User } from 'lucide-react';
import React, { useEffect, useState, useMemo } from 'react';

interface ShipmentDetailsModalProps {
    isOpen: boolean;
    onClose: () => void;
    shipment: PackageResponse;
    onShipmentUpdated?: (updatedShipment: PackageResponse) => void;
}

interface ShipmentFormData {
    tracking_number: string;
    carrier: string;
    status: PackageStatus;
    estimated_delivery?: string;
    actual_delivery?: string;
    recipient_name?: string;
    shipper_name?: string;
    package_description?: string;
    order_number?: string;
    tracking_link?: string;
}

const CARRIER_OPTIONS = [
    { value: 'fedex', label: 'FedEx' },
    { value: 'ups', label: 'UPS' },
    { value: 'usps', label: 'USPS' },
    { value: 'dhl', label: 'DHL' },
    { value: 'amazon', label: 'Amazon' },
    { value: 'ontrac', label: 'OnTrac' },
    { value: 'unknown', label: 'Unknown' },
];

const ShipmentDetailsModal: React.FC<ShipmentDetailsModalProps> = ({
    isOpen,
    onClose,
    shipment,
    onShipmentUpdated
}) => {
    const [formData, setFormData] = useState<ShipmentFormData>({
        tracking_number: '',
        carrier: 'unknown',
        status: 'pending' as PackageStatus,
        estimated_delivery: '',
        actual_delivery: '',
        recipient_name: '',
        shipper_name: '',
        package_description: '',
        order_number: '',
        tracking_link: '',
    });
    const [originalData, setOriginalData] = useState<ShipmentFormData | null>(null);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);
    const shipmentsClient = useMemo(() => new ShipmentsClient(), []);

    // Events state
    const [events, setEvents] = useState<Array<{
        id: string;
        event_date: string;
        status: PackageStatus;
        location?: string;
        description?: string;
        created_at: string;
    }>>([]);
    const [loadingEvents, setLoadingEvents] = useState(false);
    const [eventsError, setEventsError] = useState<string | null>(null);
    const [eventsToDelete, setEventsToDelete] = useState<Set<string>>(new Set());

    // Initialize form data when modal opens
    useEffect(() => {
        if (isOpen && shipment) {
            const initialData: ShipmentFormData = {
                tracking_number: shipment.tracking_number,
                carrier: shipment.carrier,
                status: shipment.status,
                estimated_delivery: shipment.estimated_delivery ? safeParseDateToISOString(shipment.estimated_delivery) : '',
                actual_delivery: shipment.actual_delivery ? safeParseDateToISOString(shipment.actual_delivery) : '',
                recipient_name: shipment.recipient_name || '',
                shipper_name: shipment.shipper_name || '',
                package_description: shipment.package_description || '',
                order_number: shipment.order_number || '',
                tracking_link: shipment.tracking_link || '',
            };

            setFormData(initialData);
            setOriginalData(initialData);
            setError(null);
            setSuccess(false);

            // Fetch events when modal opens
            const fetchEvents = async () => {
                if (!shipment?.id) return;

                setLoadingEvents(true);
                setEventsError(null);
                try {
                    const fetchedEvents = await shipmentsClient.getTrackingEvents(shipment.id);
                    setEvents(fetchedEvents);
                } catch (err) {
                    console.error('Error fetching events:', err);
                    setEventsError(err instanceof Error ? err.message : 'Failed to fetch events');
                } finally {
                    setLoadingEvents(false);
                }
            };

            fetchEvents();
        }
    }, [isOpen, shipment, shipmentsClient]);



    // Handle event deletion (stage for deletion)
    const handleDeleteEvent = async (eventId: string) => {
        try {
            await shipmentsClient.deleteTrackingEvent(shipment.id, eventId);
            setEvents(prev => prev.filter(event => event.id !== eventId));
            setEventsToDelete(prev => {
                const newSet = new Set(prev);
                newSet.delete(eventId);
                return newSet;
            });
        } catch (err) {
            console.error('Error deleting event:', err);
            setError(err instanceof Error ? err.message : 'Failed to delete event');
        }
    };

    // Handle event restoration (unstage from deletion)
    const handleRestoreEvent = (eventId: string) => {
        setEventsToDelete(prev => {
            const newSet = new Set(prev);
            newSet.delete(eventId);
            return newSet;
        });
    };

    const handleInputChange = (field: keyof ShipmentFormData, value: string | PackageStatus) => {
        setFormData(prev => ({
            ...prev,
            [field]: value
        }));

        // Clear error when user starts typing
        if (error) {
            setError(null);
        }
    };

    const handleSave = async () => {
        setIsSaving(true);
        setError(null);

        try {
            // Prepare update data - only include fields that have changed
            const updateData: Partial<ShipmentFormData> = {};

            if (originalData) {
                Object.keys(formData).forEach(key => {
                    const field = key as keyof ShipmentFormData;
                    if (formData[field] !== originalData[field]) {
                        // Handle status field type casting
                        if (field === 'status') {
                            updateData[field] = formData[field] as PackageStatus;
                        } else {
                            updateData[field] = formData[field];
                        }
                    }
                });
            }

            // Check if there are any changes (form data or staged deletions)
            const hasFormChanges = Object.keys(updateData).length > 0;
            const hasStagedDeletions = eventsToDelete.size > 0;

            // If no changes, just close the modal
            if (!hasFormChanges && !hasStagedDeletions) {
                onClose();
                return;
            }

            // Update the shipment if there are form changes
            let updatedShipment = shipment;
            if (hasFormChanges) {
                updatedShipment = await shipmentsClient.updatePackage(shipment.id, updateData);
            }

            // Delete staged events if any
            let successfullyDeletedCount = 0;
            if (hasStagedDeletions) {
                const deletePromises = Array.from(eventsToDelete).map(async (eventId) => {
                    try {
                        await shipmentsClient.deleteTrackingEvent(shipment.id, eventId);
                        return { success: true, eventId };
                    } catch (error) {
                        console.error(`Failed to delete event ${eventId}:`, error);
                        return { success: false, eventId, error };
                    }
                });

                const results = await Promise.allSettled(deletePromises);
                const successfulDeletions = results
                    .filter((result): result is PromiseFulfilledResult<{ success: boolean; eventId: string }> =>
                        result.status === 'fulfilled' && result.value.success
                    );
                const failedDeletions = results
                    .filter((result): result is PromiseFulfilledResult<{ success: boolean; eventId: string; error: unknown }> =>
                        result.status === 'fulfilled' && !result.value.success
                    );

                successfullyDeletedCount = successfulDeletions.length;

                // Log failed deletions for debugging
                if (failedDeletions.length > 0) {
                    console.warn('Some event deletions failed:', failedDeletions);
                }

                // If any deletions failed, show a warning but continue
                if (failedDeletions.length > 0) {
                    setError(`Warning: ${failedDeletions.length} event(s) could not be deleted. Other changes were saved successfully.`);
                }
            }

            // Update the shipment object with the correct events_count
            // This handles both cases: form changes + event deletions, or just event deletions
            const finalEventsCount = Math.max(0, updatedShipment.events_count - successfullyDeletedCount);
            updatedShipment = {
                ...updatedShipment,
                events_count: finalEventsCount
            };

            // Show success message (unless there were partial failures)
            if (successfullyDeletedCount === eventsToDelete.size) {
                setSuccess(true);
            }

            // Call the callback if provided
            if (onShipmentUpdated) {
                onShipmentUpdated(updatedShipment);
            }

            // Close modal after a short delay to show success state
            setTimeout(() => {
                onClose();
                setSuccess(false);
                setError(null); // Clear any warning messages
            }, 1500);

        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to update shipment';
            setError(errorMessage);
            console.error('Error updating shipment:', err);
        } finally {
            setIsSaving(false);
        }
    };

    const handleCancel = () => {
        // Reset form data to original values
        if (originalData) {
            setFormData(originalData);
        }
        // Clear staged deletions
        setEventsToDelete(new Set());
        setError(null);
        onClose();
    };

    const hasChanges = (originalData && Object.keys(formData).some(key => {
        const field = key as keyof ShipmentFormData;
        return formData[field] !== originalData[field];
    })) || eventsToDelete.size > 0;

    if (!isOpen) return null;

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Package className="h-5 w-5" />
                        Edit Shipment Details
                    </DialogTitle>
                </DialogHeader>

                <div className="space-y-6">
                    {/* Error Alert */}
                    {error && (
                        <Alert variant="destructive">
                            <AlertDescription>{error}</AlertDescription>
                        </Alert>
                    )}

                    {/* Success Alert */}
                    {success && (
                        <Alert>
                            <AlertDescription>Shipment updated successfully!</AlertDescription>
                        </Alert>
                    )}

                    {/* Form Fields */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Tracking Number */}
                        <div className="space-y-2">
                            <Label htmlFor="tracking_number" className="flex items-center gap-2">
                                <Hash className="h-4 w-4" />
                                Tracking Number
                            </Label>
                            <Input
                                id="tracking_number"
                                value={formData.tracking_number}
                                onChange={(e) => handleInputChange('tracking_number', e.target.value)}
                                placeholder="Enter tracking number"
                            />
                            <FieldUpdateMessage
                                existingPackage={shipment}
                                currentValue={formData.tracking_number}
                                originalValue={originalData?.tracking_number}
                            />
                        </div>

                        {/* Carrier */}
                        <div className="space-y-2">
                            <Label htmlFor="carrier" className="flex items-center gap-2">
                                <Truck className="h-4 w-4" />
                                Carrier
                            </Label>
                            <Select value={formData.carrier} onValueChange={(value) => handleInputChange('carrier', value)}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select carrier" />
                                </SelectTrigger>
                                <SelectContent>
                                    {CARRIER_OPTIONS.map(option => (
                                        <SelectItem key={option.value} value={option.value}>
                                            {option.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <FieldUpdateMessage
                                existingPackage={shipment}
                                currentValue={formData.carrier}
                                originalValue={originalData?.carrier}
                            />
                        </div>

                        {/* Status */}
                        <div className="space-y-2">
                            <Label htmlFor="status" className="flex items-center gap-2">
                                <BadgeCheck className="h-4 w-4" />
                                Status
                            </Label>
                            <Select value={formData.status} onValueChange={(value) => handleInputChange('status', value as PackageStatus)}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select status" />
                                </SelectTrigger>
                                <SelectContent>
                                    {PACKAGE_STATUS_OPTIONS.map(option => (
                                        <SelectItem key={option.value} value={option.value}>
                                            {option.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <FieldUpdateMessage
                                existingPackage={shipment}
                                currentValue={formData.status}
                                originalValue={originalData?.status}
                            />
                        </div>

                        {/* Estimated Delivery */}
                        <div className="space-y-2">
                            <Label htmlFor="estimated_delivery" className="flex items-center gap-2">
                                <Calendar className="h-4 w-4" />
                                Estimated Delivery
                            </Label>
                            <Input
                                id="estimated_delivery"
                                type="date"
                                value={formData.estimated_delivery}
                                onChange={(e) => handleInputChange('estimated_delivery', e.target.value)}
                            />
                            <FieldUpdateMessage
                                existingPackage={shipment}
                                currentValue={formData.estimated_delivery || ''}
                                originalValue={originalData?.estimated_delivery}
                            />
                        </div>

                        {/* Actual Delivery */}
                        <div className="space-y-2">
                            <Label htmlFor="actual_delivery" className="flex items-center gap-2">
                                <Calendar className="h-4 w-4" />
                                Actual Delivery
                            </Label>
                            <Input
                                id="actual_delivery"
                                type="date"
                                value={formData.actual_delivery}
                                onChange={(e) => handleInputChange('actual_delivery', e.target.value)}
                            />
                            <FieldUpdateMessage
                                existingPackage={shipment}
                                currentValue={formData.actual_delivery || ''}
                                originalValue={originalData?.actual_delivery}
                            />
                        </div>

                        {/* Recipient Name */}
                        <div className="space-y-2">
                            <Label htmlFor="recipient_name" className="flex items-center gap-2">
                                <User className="h-4 w-4" />
                                Recipient Name
                            </Label>
                            <Input
                                id="recipient_name"
                                value={formData.recipient_name}
                                onChange={(e) => handleInputChange('recipient_name', e.target.value)}
                                placeholder="Enter recipient name"
                            />
                            <FieldUpdateMessage
                                existingPackage={shipment}
                                currentValue={formData.recipient_name || ''}
                                originalValue={originalData?.recipient_name}
                            />
                        </div>

                        {/* Shipper Name */}
                        <div className="space-y-2">
                            <Label htmlFor="shipper_name" className="flex items-center gap-2">
                                <User className="h-4 w-4" />
                                Shipper Name
                            </Label>
                            <Input
                                id="shipper_name"
                                value={formData.shipper_name}
                                onChange={(e) => handleInputChange('shipper_name', e.target.value)}
                                placeholder="Enter shipper name"
                            />
                            <FieldUpdateMessage
                                existingPackage={shipment}
                                currentValue={formData.shipper_name || ''}
                                originalValue={originalData?.shipper_name}
                            />
                        </div>

                        {/* Order Number */}
                        <div className="space-y-2">
                            <Label htmlFor="order_number" className="flex items-center gap-2">
                                <Tag className="h-4 w-4" />
                                Order Number
                            </Label>
                            <Input
                                id="order_number"
                                value={formData.order_number}
                                onChange={(e) => handleInputChange('order_number', e.target.value)}
                                placeholder="Enter order number"
                            />
                            <FieldUpdateMessage
                                existingPackage={shipment}
                                currentValue={formData.order_number || ''}
                                originalValue={originalData?.order_number}
                            />
                        </div>

                        {/* Tracking Link */}
                        <div className="space-y-2">
                            <Label htmlFor="tracking_link" className="flex items-center gap-2">
                                <ExternalLink className="h-4 w-4" />
                                Tracking Link
                            </Label>
                            <Input
                                id="tracking_link"
                                value={formData.tracking_link}
                                onChange={(e) => handleInputChange('tracking_link', e.target.value)}
                                placeholder="Enter tracking URL"
                            />
                            <FieldUpdateMessage
                                existingPackage={shipment}
                                currentValue={formData.tracking_link || ''}
                                originalValue={originalData?.tracking_link}
                            />
                        </div>
                    </div>

                    {/* Package Description - Full Width */}
                    <div className="space-y-2">
                        <Label htmlFor="package_description" className="flex items-center gap-2">
                            <FileText className="h-4 w-4" />
                            Package Description
                        </Label>
                        <Textarea
                            id="package_description"
                            value={formData.package_description}
                            onChange={(e) => handleInputChange('package_description', e.target.value)}
                            placeholder="Enter package description"
                            rows={3}
                        />
                        <FieldUpdateMessage
                            existingPackage={shipment}
                            currentValue={formData.package_description || ''}
                            originalValue={originalData?.package_description}
                        />
                    </div>

                    {/* Tracking Events Section */}
                    <div className="space-y-2">
                        <Label className="flex items-center gap-2">
                            <Calendar className="h-4 w-4" />
                            Tracking Events
                        </Label>
                        {loadingEvents ? (
                            <div className="text-sm text-gray-500 flex items-center gap-2">
                                <Loader2 className="h-4 w-4 animate-spin" />
                                Loading events...
                            </div>
                        ) : eventsError ? (
                            <div className="text-sm text-red-500">{eventsError}</div>
                        ) : events.length === 0 ? (
                            <div className="text-sm text-gray-500">No tracking events found.</div>
                        ) : (
                            <ol className="border-l-2 border-blue-500 pl-4">
                                {events.map((event, idx) => {
                                    const isMarkedForDeletion = eventsToDelete.has(event.id);
                                    return (
                                        <li key={idx} className="mb-4">
                                            <div className="flex items-start justify-between">
                                                <div className="flex-1">
                                                    <div className="text-xs text-gray-400">{safeParseDateToLocaleString(event.event_date, {
                                                        year: 'numeric',
                                                        month: 'short',
                                                        day: 'numeric',
                                                        hour: '2-digit',
                                                        minute: '2-digit'
                                                    })}</div>
                                                    <div className={`font-semibold ${isMarkedForDeletion ? 'line-through text-gray-400' : ''}`}>
                                                        {isMarkedForDeletion && <Trash2 className="inline h-4 w-4 mr-2 text-red-500" />}
                                                        {event.status}
                                                    </div>
                                                    {event.location && <div className={`text-sm ${isMarkedForDeletion ? 'text-gray-300' : 'text-gray-500'}`}>{event.location}</div>}
                                                    {event.description && <div className={`text-xs ${isMarkedForDeletion ? 'text-gray-300' : 'text-gray-400'}`}>{event.description}</div>}
                                                </div>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => isMarkedForDeletion ? handleRestoreEvent(event.id) : handleDeleteEvent(event.id)}
                                                    className="ml-2 h-8 w-8 p-0 text-gray-400 hover:text-red-500 hover:bg-red-50"
                                                    aria-label={isMarkedForDeletion ? "Restore tracking event" : "Delete tracking event"}
                                                >
                                                    {isMarkedForDeletion ? (
                                                        <span className="text-xs">↶</span>
                                                    ) : (
                                                        <Trash2 className="h-4 w-4" />
                                                    )}
                                                </Button>
                                            </div>
                                        </li>
                                    );
                                })}
                            </ol>
                        )}
                    </div>
                </div>

                <DialogFooter className="flex gap-2">
                    <Button
                        variant="outline"
                        onClick={handleCancel}
                        disabled={isSaving}
                    >
                        Cancel
                    </Button>
                    <Button
                        onClick={handleSave}
                        disabled={isSaving || !hasChanges}
                    >
                        {isSaving ? (
                            <>
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                Saving...
                            </>
                        ) : (
                            'Save Changes'
                        )}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};

export default ShipmentDetailsModal;
