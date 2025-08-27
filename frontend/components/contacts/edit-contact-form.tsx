import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import type { Contact, EmailContactUpdate } from '@/types/api/contacts';
import { Calendar, Edit, ExternalLink, FileText, Mail, Merge, Plus, Tag, X } from 'lucide-react';
import React, { useState } from 'react';

interface EditContactFormProps {
    contact: Contact;
    onSubmit: (id: string, contactData: EmailContactUpdate) => void;
    onCancel: () => void;
    onMerge?: (contact: Contact) => void;
    isLoading?: boolean;
}

const EditContactForm: React.FC<EditContactFormProps> = ({
    contact,
    onSubmit,
    onCancel,
    onMerge,
    isLoading = false,
}) => {
    const [formData, setFormData] = useState<EmailContactUpdate>({
        display_name: contact.display_name || '',
        given_name: contact.given_name || '',
        family_name: contact.family_name || '',
        tags: contact.tags || [],
        notes: contact.notes || '',
    });

    const [newTag, setNewTag] = useState('');
    const [errors, setErrors] = useState<Record<string, string>>({});
    const [showMergeOptions, setShowMergeOptions] = useState(false);

    const validateForm = (): boolean => {
        const newErrors: Record<string, string> = {};

        if (!formData.display_name && !formData.given_name && !formData.family_name) {
            newErrors.display_name = 'At least one name field is required';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();

        if (validateForm()) {
            onSubmit(contact.id!, formData);
        }
    };

    const handleInputChange = (field: keyof EmailContactUpdate, value: string | string[]) => {
        setFormData(prev => ({ ...prev, [field]: value }));

        // Clear error when user starts typing
        if (errors[field]) {
            setErrors(prev => ({ ...prev, [field]: '' }));
        }
    };

    const addTag = () => {
        if (newTag.trim() && !formData.tags.includes(newTag.trim())) {
            handleInputChange('tags', [...formData.tags, newTag.trim()]);
            setNewTag('');
        }
    };

    const removeTag = (tagToRemove: string) => {
        handleInputChange('tags', formData.tags.filter(tag => tag !== tagToRemove));
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            addTag();
        }
    };

    const getSourceServiceIcon = (service: string) => {
        switch (service) {
            case 'office':
                return <ExternalLink className="w-4 h-4" />;
            case 'email':
                return <Mail className="w-4 h-4" />;
            case 'calendar':
                return <Calendar className="w-4 h-4" />;
            case 'documents':
                return <FileText className="w-4 h-4" />;
            default:
                return null;
        }
    };

    const getSourceServiceColor = (service: string) => {
        switch (service) {
            case 'office':
                return 'bg-blue-100 text-blue-800 border-blue-200';
            case 'email':
                return 'bg-green-100 text-green-800 border-green-200';
            case 'calendar':
                return 'bg-purple-100 text-purple-800 border-purple-200';
            case 'documents':
                return 'bg-orange-100 text-orange-800 border-orange-200';
            default:
                return 'bg-gray-100 text-gray-800 border-gray-200';
        }
    };

    const hasOfficeIntegration = contact.source_services?.includes('office') || false;
    const hasDiscoveredData = contact.source_services?.some(s => ['email', 'calendar', 'documents'].includes(s)) || false;
    const canMerge = hasOfficeIntegration && hasDiscoveredData;

    return (
        <div className="bg-white rounded-lg shadow-lg p-6 max-w-4xl mx-auto">
            <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-gray-900">Edit Contact</h2>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={onCancel}
                    disabled={isLoading}
                >
                    <X className="w-4 h-4" />
                </Button>
            </div>

            {/* Contact Overview */}
            <div className="bg-gray-50 rounded-lg p-4 mb-6">
                <div className="flex items-center gap-4">
                    <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-semibold text-xl">
                        {(contact.display_name || contact.email_address || '').slice(0, 2).toUpperCase()}
                    </div>

                    <div className="flex-1">
                        <h3 className="text-lg font-semibold text-gray-900">
                            {contact.display_name || contact.email_address}
                        </h3>
                        <p className="text-gray-600">{contact.email_address}</p>

                        {/* Source Services */}
                        <div className="flex gap-2 mt-2">
                            {contact.source_services?.map(service => (
                                <span
                                    key={service}
                                    className={`inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full border ${getSourceServiceColor(service)}`}
                                >
                                    {getSourceServiceIcon(service)}
                                    {service}
                                </span>
                            ))}
                        </div>
                    </div>

                    {/* Merge Button */}
                    {canMerge && onMerge && (
                        <Button
                            onClick={() => onMerge(contact)}
                            variant="outline"
                            size="sm"
                            className="flex items-center gap-2"
                        >
                            <Merge className="w-4 h-4" />
                            Merge Sources
                        </Button>
                    )}
                </div>

                {/* Source Information */}
                <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div>
                        <h4 className="font-medium text-gray-700 mb-2">Source Information</h4>
                        <div className="space-y-1">
                            <div className="flex justify-between">
                                <span className="text-gray-600">Total Events:</span>
                                <span className="font-medium">{contact.total_event_count || 0}</span>
                            </div>

                            <div className="flex justify-between">
                                <span className="text-gray-600">Last Seen:</span>
                                <span className="font-medium">
                                    {new Date(contact.last_seen).toLocaleDateString()}
                                </span>
                            </div>
                        </div>
                    </div>

                    <div>
                        <h4 className="font-medium text-gray-700 mb-2">Event Counts</h4>
                        <div className="space-y-1">
                            {contact.event_counts && Object.keys(contact.event_counts).length > 0 ? (
                                Object.entries(contact.event_counts).map(([eventType, count]) => (
                                    <div key={eventType} className="flex justify-between">
                                        <span className="text-gray-600 capitalize">{eventType}:</span>
                                        <span className="font-medium">{count.count}</span>
                                    </div>
                                ))
                            ) : (
                                <span className="text-gray-500">No events recorded</span>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
                {/* Name Fields */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="space-y-2">
                        <Label htmlFor="display_name" className="flex items-center gap-2">
                            <Edit className="w-4 h-4" />
                            Display Name
                        </Label>
                        <Input
                            id="display_name"
                            placeholder="Full Name"
                            value={formData.display_name}
                            onChange={(e) => handleInputChange('display_name', e.target.value)}
                            className={errors.display_name ? 'border-red-500' : ''}
                            disabled={isLoading}
                        />
                        {errors.display_name && (
                            <p className="text-sm text-red-600">{errors.display_name}</p>
                        )}
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="given_name">First Name</Label>
                        <Input
                            id="given_name"
                            placeholder="First Name"
                            value={formData.given_name}
                            onChange={(e) => handleInputChange('given_name', e.target.value)}
                            disabled={isLoading}
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="family_name">Last Name</Label>
                        <Input
                            id="family_name"
                            placeholder="Last Name"
                            value={formData.family_name}
                            onChange={(e) => handleInputChange('family_name', e.target.value)}
                            disabled={isLoading}
                        />
                    </div>
                </div>

                {/* Tags */}
                <div className="space-y-2">
                    <Label htmlFor="tags" className="flex items-center gap-2">
                        <Tag className="w-4 h-4" />
                        Tags
                    </Label>
                    <div className="flex gap-2">
                        <Input
                            id="tags"
                            placeholder="Add tags (press Enter)"
                            value={newTag}
                            onChange={(e) => setNewTag(e.target.value)}
                            onKeyPress={handleKeyPress}
                            disabled={isLoading}
                        />
                        <Button
                            type="button"
                            onClick={addTag}
                            disabled={!newTag.trim() || isLoading}
                            variant="outline"
                            size="sm"
                        >
                            <Plus className="w-4 h-4" />
                        </Button>
                    </div>

                    {/* Display existing tags */}
                    {formData.tags.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-2">
                            {formData.tags.map((tag) => (
                                <Badge
                                    key={tag}
                                    variant="secondary"
                                    className="flex items-center gap-1"
                                >
                                    {tag}
                                    <button
                                        type="button"
                                        onClick={() => removeTag(tag)}
                                        className="hover:text-red-500"
                                        disabled={isLoading}
                                    >
                                        <X className="w-3 h-3" />
                                    </button>
                                </Badge>
                            ))}
                        </div>
                    )}
                </div>

                {/* Notes */}
                <div className="space-y-2">
                    <Label htmlFor="notes">Notes</Label>
                    <Textarea
                        id="notes"
                        placeholder="Additional notes about this contact..."
                        value={formData.notes}
                        onChange={(e) => handleInputChange('notes', e.target.value)}
                        rows={3}
                        disabled={isLoading}
                    />
                </div>

                {/* Source Service Management */}
                <div className="space-y-2">
                    <Label className="flex items-center gap-2">
                        <Edit className="w-4 h-4" />
                        Source Services
                    </Label>
                    <div className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg">
                        <p className="mb-2">
                            This contact is currently associated with the following sources:
                        </p>
                        <div className="flex flex-wrap gap-2">
                            {contact.source_services?.map(service => (
                                <span
                                    key={service}
                                    className={`inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full border ${getSourceServiceColor(service)}`}
                                >
                                    {getSourceServiceIcon(service)}
                                    {service}
                                </span>
                            ))}
                        </div>
                        <p className="mt-2 text-xs text-gray-500">
                            Source services are automatically managed based on where the contact appears.
                            You cannot manually modify these through the edit form.
                        </p>
                    </div>
                </div>

                {/* Form Actions */}
                <div className="flex gap-3 pt-4 border-t border-gray-200">
                    <Button
                        type="submit"
                        disabled={isLoading}
                        className="flex-1"
                    >
                        {isLoading ? 'Updating...' : 'Update Contact'}
                    </Button>

                    <Button
                        type="button"
                        variant="outline"
                        onClick={onCancel}
                        disabled={isLoading}
                        className="flex-1"
                    >
                        Cancel
                    </Button>
                </div>
            </form>

            {/* Help Text */}
            <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                <h4 className="text-sm font-medium text-gray-700 mb-2">Editing Tips:</h4>
                <ul className="text-xs text-gray-600 space-y-1">
                    <li>• Changes will be applied to all source services where this contact appears</li>
                    <li>• Source services are automatically managed and cannot be manually modified</li>
                    <li>• Use the merge option if you have duplicate contacts from different sources</li>
                    <li>• Tags and notes help organize and find contacts later</li>
                </ul>
            </div>
        </div>
    );
};

export default EditContactForm;
