import React from 'react';
import type { Contact } from '@/types/api/contacts';
import { Edit, Trash2, Merge, ExternalLink, Calendar, Mail, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ContactCardProps {
  contact: Contact;
  onEdit?: (contact: Contact) => void;
  onDelete?: (contact: Contact) => void;
  onMerge?: (contact: Contact) => void;
  onViewDetails?: (contact: Contact) => void;
}

const ContactCard: React.FC<ContactCardProps> = ({
  contact,
  onEdit,
  onDelete,
  onMerge,
  onViewDetails,
}) => {
  const getSourceServiceIcon = (service: string) => {
    switch (service) {
      case 'office':
        return <ExternalLink className="w-3 h-3" />;
      case 'email':
        return <Mail className="w-3 h-3" />;
      case 'calendar':
        return <Calendar className="w-3 h-3" />;
      case 'documents':
        return <FileText className="w-3 h-3" />;
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

  return (
    <div className="bg-white border rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
      {/* Header with avatar and name */}
      <div className="flex items-start gap-3 mb-3">
        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-semibold text-lg flex-shrink-0">
          {getInitials()}
        </div>
        
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-gray-900 truncate">
            {getPrimaryName()}
          </h3>
          <p className="text-sm text-gray-600 truncate">
            {contact.email_address}
          </p>
          
          {/* Source Services Badges */}
          <div className="flex flex-wrap gap-1 mt-2">
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
      </div>

      {/* Contact Details */}
      <div className="space-y-2 mb-3">
        {/* Relevance Score */}
        {contact.relevance_score !== undefined && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500 font-medium">Relevance:</span>
            <div className="flex-1 bg-gray-200 rounded-full h-2">
              <div
                className="bg-gradient-to-r from-blue-500 to-purple-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${(contact.relevance_score || 0) * 100}%` }}
              />
            </div>
            <span className="text-xs text-gray-600 font-medium min-w-[3rem] text-right">
              {Math.round((contact.relevance_score || 0) * 100)}%
            </span>
          </div>
        )}

        {/* Event Counts */}
        {contact.event_counts && Object.keys(contact.event_counts).length > 0 && (
          <div className="flex flex-wrap gap-2">
            {Object.entries(contact.event_counts).map(([eventType, count]) => (
              <span
                key={eventType}
                className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-gray-50 text-gray-700 rounded border"
              >
                {getSourceServiceIcon(eventType)}
                {eventType}: {count.count}
              </span>
            ))}
          </div>
        )}

        {/* Tags */}
        {contact.tags && contact.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {contact.tags.slice(0, 3).map(tag => (
              <span
                key={tag}
                className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-full"
              >
                {tag}
              </span>
            ))}
            {contact.tags.length > 3 && (
              <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-full">
                +{contact.tags.length - 3}
              </span>
            )}
          </div>
        )}

        {/* Notes Preview */}
        {contact.notes && (
          <p className="text-xs text-gray-600 line-clamp-2">
            {contact.notes}
          </p>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2 pt-2 border-t border-gray-100">
        {onViewDetails && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onViewDetails(contact)}
            className="flex-1 text-xs"
          >
            View Details
          </Button>
        )}
        
        {onEdit && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => onEdit(contact)}
            className="text-xs"
          >
            <Edit className="w-3 h-3 mr-1" />
            Edit
          </Button>
        )}
        
        {onMerge && hasDiscoveredData && hasOfficeIntegration && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => onMerge(contact)}
            className="text-xs"
          >
            <Merge className="w-3 h-3 mr-1" />
            Merge
          </Button>
        )}
        
        {onDelete && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => onDelete(contact)}
            className="text-xs text-red-600 hover:text-red-700 hover:bg-red-50"
          >
            <Trash2 className="w-3 h-3 mr-1" />
            Delete
          </Button>
        )}
      </div>

      {/* Footer with timestamps */}
      <div className="mt-3 pt-2 border-t border-gray-100 text-xs text-gray-500">
        <div className="flex justify-between">
          <span>Last seen: {new Date(contact.last_seen).toLocaleDateString()}</span>
          <span>Created: {new Date(contact.created_at || '').toLocaleDateString()}</span>
        </div>
      </div>
    </div>
  );
};

export default ContactCard;
