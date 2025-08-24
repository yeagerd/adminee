import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { Contact } from '@/types/api/contacts';
import { Calendar, Edit, ExternalLink, FileText, Mail, Merge, Trash2, X } from 'lucide-react';
import React from 'react';

interface ContactDetailModalProps {
    contact: Contact;
    isOpen: boolean;
    onClose: () => void;
    onEdit?: (contact: Contact) => void;
    onDelete?: (contact: Contact) => void;
    onMerge?: (contact: Contact) => void;
}

const ContactDetailModal: React.FC<ContactDetailModalProps> = ({
    contact,
    isOpen,
    onClose,
    onEdit,
    onDelete,
    onMerge,
}) => {
    if (!isOpen) return null;

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

    const getPrimaryName = () => {
        if (contact.display_name) return contact.display_name;
        if (contact.given_name && contact.family_name) {
            return `${contact.given_name} ${contact.family_name}`;
        }
        if (contact.given_name) return contact.given_name;
        if (contact.family_name) return contact.family_name;
        return contact.email_address;
    };

    const getInitials = () => {
        const name = getPrimaryName();
        if (name === contact.email_address) {
            return contact.email_address.slice(0, 2).toUpperCase();
        }
        return name.slice(0, 2).toUpperCase();
    };

    const hasOfficeIntegration = contact.source_services?.includes('office') || false;
    const hasDiscoveredData = contact.source_services?.some(s => ['email', 'calendar', 'documents'].includes(s)) || false;
    const canMerge = hasOfficeIntegration && hasDiscoveredData;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-200">
                    <h2 className="text-2xl font-bold text-gray-900">Contact Details</h2>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={onClose}
                    >
                        <X className="w-5 h-5" />
                    </Button>
                </div>

                {/* Content */}
                <div className="p-6 space-y-6">
                    {/* Contact Header */}
                    <div className="flex items-start gap-6">
                        <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-semibold text-2xl flex-shrink-0">
                            {getInitials()}
                        </div>

                        <div className="flex-1 min-w-0">
                            <h3 className="text-xl font-semibold text-gray-900 mb-2">
                                {getPrimaryName()}
                            </h3>
                            <p className="text-lg text-gray-600 mb-3">{contact.email_address}</p>

                            {/* Source Services */}
                            <div className="flex flex-wrap gap-2">
                                {contact.source_services?.map(service => (
                                    <span
                                        key={service}
                                        className={`inline-flex items-center gap-1 px-3 py-1 text-sm rounded-full border ${getSourceServiceColor(service)}`}
                                    >
                                        {getSourceServiceIcon(service)}
                                        {service}
                                    </span>
                                ))}
                            </div>
                        </div>

                        {/* Action Buttons */}
                        <div className="flex flex-col gap-2">
                            {onEdit && (
                                <Button
                                    onClick={() => onEdit(contact)}
                                    variant="outline"
                                    size="sm"
                                    className="flex items-center gap-2"
                                >
                                    <Edit className="w-4 h-4" />
                                    Edit
                                </Button>
                            )}

                            {canMerge && onMerge && (
                                <Button
                                    onClick={() => onMerge(contact)}
                                    variant="outline"
                                    size="sm"
                                    className="flex items-center gap-2"
                                >
                                    <Merge className="w-4 h-4" />
                                    Merge
                                </Button>
                            )}

                            {onDelete && (
                                <Button
                                    onClick={() => onDelete(contact)}
                                    variant="destructive"
                                    size="sm"
                                    className="flex items-center gap-2"
                                >
                                    <Trash2 className="w-4 h-4" />
                                    Delete
                                </Button>
                            )}
                        </div>
                    </div>

                    {/* Contact Information Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Basic Information */}
                        <div className="space-y-4">
                            <h4 className="text-lg font-semibold text-gray-900">Basic Information</h4>

                            <div className="space-y-3">
                                {contact.given_name && (
                                    <div>
                                        <span className="text-sm font-medium text-gray-600">First Name:</span>
                                        <p className="text-gray-900">{contact.given_name}</p>
                                    </div>
                                )}

                                {contact.family_name && (
                                    <div>
                                        <span className="text-sm font-medium text-gray-600">Last Name:</span>
                                        <p className="text-gray-900">{contact.family_name}</p>
                                    </div>
                                )}

                                <div>
                                    <span className="text-sm font-medium text-gray-600">Email Address:</span>
                                    <p className="text-gray-900">{contact.email_address}</p>
                                </div>

                                {contact.tags && contact.tags.length > 0 && (
                                    <div>
                                        <span className="text-sm font-medium text-gray-600">Tags:</span>
                                        <div className="flex flex-wrap gap-2 mt-1">
                                            {contact.tags.map(tag => (
                                                <Badge key={tag} variant="secondary">
                                                    {tag}
                                                </Badge>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {contact.notes && (
                                    <div>
                                        <span className="text-sm font-medium text-gray-600">Notes:</span>
                                        <p className="text-gray-900 mt-1">{contact.notes}</p>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Statistics & Metrics */}
                        <div className="space-y-4">
                            <h4 className="text-lg font-semibold text-gray-900">Statistics & Metrics</h4>

                            <div className="space-y-3">
                                <div>
                                    <span className="text-sm font-medium text-gray-600">Relevance Score:</span>
                                    <div className="flex items-center gap-3 mt-1">
                                        <div className="flex-1 bg-gray-200 rounded-full h-3">
                                            <div
                                                className="bg-gradient-to-r from-blue-500 to-purple-600 h-3 rounded-full transition-all duration-300"
                                                style={{ width: `${(contact.relevance_score || 0) * 100}%` }}
                                            />
                                        </div>
                                        <span className="text-sm font-medium text-gray-900 min-w-[3rem]">
                                            {Math.round((contact.relevance_score || 0) * 100)}%
                                        </span>
                                    </div>
                                </div>

                                <div>
                                    <span className="text-sm font-medium text-gray-600">Total Events:</span>
                                    <p className="text-gray-900">{contact.total_event_count || 0}</p>
                                </div>

                                <div>
                                    <span className="text-sm font-medium text-gray-600">Last Seen:</span>
                                    <p className="text-gray-900">
                                        {new Date(contact.last_seen).toLocaleDateString()} at{' '}
                                        {new Date(contact.last_seen).toLocaleTimeString()}
                                    </p>
                                </div>

                                <div>
                                    <span className="text-sm font-medium text-gray-600">First Seen:</span>
                                    <p className="text-gray-900">
                                        {new Date(contact.first_seen).toLocaleDateString()} at{' '}
                                        {new Date(contact.first_seen).toLocaleTimeString()}
                                    </p>
                                </div>

                                <div>
                                    <span className="text-sm font-medium text-gray-600">Created:</span>
                                    <p className="text-gray-900">
                                        {new Date(contact.created_at || '').toLocaleDateString()} at{' '}
                                        {new Date(contact.created_at || '').toLocaleTimeString()}
                                    </p>
                                </div>

                                <div>
                                    <span className="text-sm font-medium text-gray-600">Last Updated:</span>
                                    <p className="text-gray-900">
                                        {new Date(contact.updated_at || '').toLocaleDateString()} at{' '}
                                        {new Date(contact.updated_at || '').toLocaleTimeString()}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Event Counts */}
                    {contact.event_counts && Object.keys(contact.event_counts).length > 0 && (
                        <div className="space-y-4">
                            <h4 className="text-lg font-semibold text-gray-900">Event Activity</h4>

                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {Object.entries(contact.event_counts).map(([eventType, count]) => (
                                    <div
                                        key={eventType}
                                        className="bg-gray-50 rounded-lg p-4 border border-gray-200"
                                    >
                                        <div className="flex items-center gap-3 mb-2">
                                            {getSourceServiceIcon(eventType)}
                                            <span className="font-medium text-gray-900 capitalize">
                                                {eventType}
                                            </span>
                                        </div>
                                        <div className="text-2xl font-bold text-gray-900">
                                            {count.count}
                                        </div>
                                        <div className="text-sm text-gray-600">
                                            {count.count === 1 ? 'event' : 'events'}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Source Service Details */}
                    <div className="space-y-4">
                        <h4 className="text-lg font-semibold text-gray-900">Source Service Details</h4>

                        <div className="space-y-3">
                            {contact.source_services?.map(service => (
                                <div
                                    key={service}
                                    className={`p-4 rounded-lg border ${getSourceServiceColor(service)}`}
                                >
                                    <div className="flex items-center gap-3">
                                        {getSourceServiceIcon(service)}
                                        <span className="font-medium capitalize">{service}</span>
                                    </div>

                                    <div className="mt-2 text-sm">
                                        {service === 'office' && (
                                            <p>This contact is synced from your office integration (Google/Microsoft)</p>
                                        )}
                                        {service === 'email' && (
                                            <p>This contact was discovered from email communications</p>
                                        )}
                                        {service === 'calendar' && (
                                            <p>This contact was discovered from calendar events</p>
                                        )}
                                        {service === 'documents' && (
                                            <p>This contact was discovered from document interactions</p>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Relevance Factors */}
                    {contact.relevance_score !== undefined && (
                        <div className="space-y-4">
                            <h4 className="text-lg font-semibold text-gray-900">Relevance Factors</h4>

                            <div className="bg-gray-50 rounded-lg p-4">
                                <p className="text-sm text-gray-600 mb-3">
                                    Relevance score is calculated based on multiple factors:
                                </p>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                                    <div className="space-y-2">
                                        <div className="flex justify-between">
                                            <span className="text-gray-600">Recency:</span>
                                            <span className="font-medium">
                                                {new Date(contact.last_seen).getTime() > Date.now() - 7 * 24 * 60 * 60 * 1000 ? 'High' : 'Medium'}
                                            </span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-gray-600">Frequency:</span>
                                            <span className="font-medium">
                                                {(contact.total_event_count || 0) > 10 ? 'High' : (contact.total_event_count || 0) > 3 ? 'Medium' : 'Low'}
                                            </span>
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <div className="flex justify-between">
                                            <span className="text-gray-600">Diversity:</span>
                                            <span className="font-medium">
                                                {(contact.source_services?.length || 0) > 1 ? 'High' : 'Low'}
                                            </span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-gray-600">Name Completeness:</span>
                                            <span className="font-medium">
                                                {contact.display_name || (contact.given_name && contact.family_name) ? 'High' : 'Low'}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex justify-end gap-3 p-6 border-t border-gray-200">
                    <Button
                        onClick={onClose}
                        variant="outline"
                    >
                        Close
                    </Button>

                    {onEdit && (
                        <Button
                            onClick={() => onEdit(contact)}
                        >
                            <Edit className="w-4 h-4 mr-2" />
                            Edit Contact
                        </Button>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ContactDetailModal;
