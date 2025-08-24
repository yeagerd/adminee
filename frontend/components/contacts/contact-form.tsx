import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import type { ContactCreate } from '@/types/api/contacts';
import { Mail, Plus, Tag, User, X } from 'lucide-react';
import React, { useState } from 'react';

interface ContactFormProps {
    onSubmit: (contactData: ContactCreate) => void;
    onCancel: () => void;
    isLoading?: boolean;
    initialData?: Partial<ContactCreate>;
}

const ContactForm: React.FC<ContactFormProps> = ({
    onSubmit,
    onCancel,
    isLoading = false,
    initialData,
}) => {
    const [formData, setFormData] = useState<ContactCreate>({
        user_id: initialData?.user_id || '',
        email_address: initialData?.email_address || '',
        display_name: initialData?.display_name || '',
        given_name: initialData?.given_name || '',
        family_name: initialData?.family_name || '',
        tags: initialData?.tags || [],
        notes: initialData?.notes || '',
    });

    const [newTag, setNewTag] = useState('');
    const [errors, setErrors] = useState<Record<string, string>>({});

    const validateForm = (): boolean => {
        const newErrors: Record<string, string> = {};

        if (!formData.email_address) {
            newErrors.email_address = 'Email address is required';
        } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email_address)) {
            newErrors.email_address = 'Please enter a valid email address';
        }

        if (!formData.display_name && !formData.given_name && !formData.family_name) {
            newErrors.display_name = 'At least one name field is required';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();

        if (validateForm()) {
            onSubmit(formData);
        }
    };

    const handleInputChange = (field: keyof ContactCreate, value: string | string[]) => {
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

    return (
        <div className="bg-white rounded-lg shadow-lg p-6 max-w-2xl mx-auto">
            <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-gray-900">Add New Contact</h2>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={onCancel}
                    disabled={isLoading}
                >
                    <X className="w-4 h-4" />
                </Button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
                {/* Email Address - Required */}
                <div className="space-y-2">
                    <Label htmlFor="email_address" className="flex items-center gap-2">
                        <Mail className="w-4 h-4" />
                        Email Address *
                    </Label>
                    <Input
                        id="email_address"
                        type="email"
                        placeholder="contact@example.com"
                        value={formData.email_address}
                        onChange={(e) => handleInputChange('email_address', e.target.value)}
                        className={errors.email_address ? 'border-red-500' : ''}
                        disabled={isLoading}
                    />
                    {errors.email_address && (
                        <p className="text-sm text-red-600">{errors.email_address}</p>
                    )}
                </div>

                {/* Name Fields */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="space-y-2">
                        <Label htmlFor="display_name" className="flex items-center gap-2">
                            <User className="w-4 h-4" />
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

                {/* Form Actions */}
                <div className="flex gap-3 pt-4 border-t border-gray-200">
                    <Button
                        type="submit"
                        disabled={isLoading}
                        className="flex-1"
                    >
                        {isLoading ? 'Creating...' : 'Create Contact'}
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
                <h4 className="text-sm font-medium text-gray-700 mb-2">Tips:</h4>
                <ul className="text-xs text-gray-600 space-y-1">
                    <li>• Email address is required and must be unique</li>
                    <li>• At least one name field should be filled</li>
                    <li>• Tags help organize and find contacts later</li>
                    <li>• Notes can include any additional information</li>
                </ul>
            </div>
        </div>
    );
};

export default ContactForm;
