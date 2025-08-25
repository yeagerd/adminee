import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import type { Contact } from '@/types/api/contacts';
import { Calendar, ExternalLink, FileText, Mail, Merge, RefreshCw, Search, X } from 'lucide-react';
import React, { useState } from 'react';

interface ContactMergerProps {
    onClose: () => void;
    onMerge: (primaryContact: Contact, secondaryContacts: Contact[]) => Promise<void>;
}

interface DuplicateGroup {
    id: string;
    contacts: Contact[];
    confidence: number;
    reason: string;
}

const ContactMerger: React.FC<ContactMergerProps> = ({ onClose, onMerge }) => {
    const [duplicateGroups, setDuplicateGroups] = useState<DuplicateGroup[]>([
        {
            id: '1',
            contacts: [
                {
                    id: '1',
                    user_id: 'user1',
                    email_address: 'john.doe@example.com',
                    display_name: 'John Doe',
                    given_name: 'John',
                    family_name: 'Doe',
                    source_services: ['office'],
                    event_counts: { email: { count: 15, last_seen: '2024-01-15T10:00:00Z' } },
                    total_event_count: 15,
                    relevance_score: 0.8,
                    last_seen: '2024-01-15T10:00:00Z',
                    first_seen: '2024-01-01T00:00:00Z',
                    tags: ['work', 'important'],
                    notes: 'Senior developer at Example Corp',
                    created_at: '2024-01-01T00:00:00Z',
                    updated_at: '2024-01-15T10:00:00Z',
                },
                {
                    id: '2',
                    user_id: 'user1',
                    email_address: 'john.doe@example.com',
                    display_name: 'John Doe',
                    given_name: 'John',
                    family_name: 'Doe',
                    source_services: ['email'],
                    event_counts: { email: { count: 8, last_seen: '2024-01-14T15:30:00Z' } },
                    total_event_count: 8,
                    relevance_score: 0.6,
                    last_seen: '2024-01-14T15:30:00Z',
                    first_seen: '2024-01-05T00:00:00Z',
                    tags: ['client'],
                    notes: 'Client contact from email communications',
                    created_at: '2024-01-05T00:00:00Z',
                    updated_at: '2024-01-14T15:30:00Z',
                }
            ],
            confidence: 0.95,
            reason: 'Exact email match with similar names'
        },
        {
            id: '2',
            contacts: [
                {
                    id: '3',
                    user_id: 'user1',
                    email_address: 'jane.smith@company.com',
                    display_name: 'Jane Smith',
                    given_name: 'Jane',
                    family_name: 'Smith',
                    source_services: ['office'],
                    event_counts: { calendar: { count: 3, last_seen: '2024-01-10T14:00:00Z' } },
                    total_event_count: 3,
                    relevance_score: 0.4,
                    last_seen: '2024-01-10T14:00:00Z',
                    first_seen: '2024-01-08T00:00:00Z',
                    tags: ['meeting'],
                    notes: 'Meeting attendee',
                    created_at: '2024-01-08T00:00:00Z',
                    updated_at: '2024-01-10T14:00:00Z',
                },
                {
                    id: '4',
                    user_id: 'user1',
                    email_address: 'jane.smith@company.com',
                    display_name: 'Jane Smith',
                    given_name: 'Jane',
                    family_name: 'Smith',
                    source_services: ['email'],
                    event_counts: { email: { count: 12, last_seen: '2024-01-13T09:15:00Z' } },
                    total_event_count: 12,
                    relevance_score: 0.7,
                    last_seen: '2024-01-13T09:15:00Z',
                    first_seen: '2024-01-02T00:00:00Z',
                    tags: ['work', 'project'],
                    notes: 'Project manager for new initiative',
                    created_at: '2024-01-02T00:00:00Z',
                    updated_at: '2024-01-13T09:15:00Z',
                }
            ],
            confidence: 0.92,
            reason: 'Exact email match with identical names'
        }
    ]);

    const [selectedGroups, setSelectedGroups] = useState<Set<string>>(new Set());
    const [primaryContacts, setPrimaryContacts] = useState<Record<string, string>>({});
    const [mergeNotes, setMergeNotes] = useState<Record<string, string>>({});
    const [isMerging, setIsMerging] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');

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

    const handleGroupToggle = (groupId: string) => {
        const newSelected = new Set(selectedGroups);
        if (newSelected.has(groupId)) {
            newSelected.delete(groupId);
        } else {
            newSelected.add(groupId);
        }
        setSelectedGroups(newSelected);
    };

    const handlePrimaryContactSelect = (groupId: string, contactId: string) => {
        setPrimaryContacts(prev => ({ ...prev, [groupId]: contactId }));
    };

    const handleMergeNotesChange = (groupId: string, notes: string) => {
        setMergeNotes(prev => ({ ...prev, [groupId]: notes }));
    };

    const handleMergeSelected = async () => {
        setIsMerging(true);
        try {
            for (const groupId of selectedGroups) {
                const group = duplicateGroups.find(g => g.id === groupId);
                if (!group) continue;

                const primaryContactId = primaryContacts[groupId];
                if (!primaryContactId) continue;

                const primaryContact = group.contacts.find(c => c.id === primaryContactId);
                const secondaryContacts = group.contacts.filter(c => c.id !== primaryContactId);

                if (primaryContact && secondaryContacts.length > 0) {
                    await onMerge(primaryContact, secondaryContacts);
                }
            }

            // Remove merged groups
            setDuplicateGroups(prev => prev.filter(g => !selectedGroups.has(g.id)));
            setSelectedGroups(new Set());
            setPrimaryContacts({});
            setMergeNotes({});
        } catch (error) {
            console.error('Error merging contacts:', error);
        } finally {
            setIsMerging(false);
        }
    };

    const filteredGroups = duplicateGroups.filter(group => {
        if (!searchQuery) return true;
        return group.contacts.some(contact =>
            contact.display_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
            contact.email_address.toLowerCase().includes(searchQuery.toLowerCase())
        );
    });

    const canMerge = selectedGroups.size > 0 &&
        Array.from(selectedGroups).every(groupId => primaryContacts[groupId]);

    return (
        <div className="bg-white rounded-lg shadow-lg p-6 max-w-6xl mx-auto">
            <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-gray-900">Contact Merger</h2>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={onClose}
                >
                    <X className="w-4 h-4" />
                </Button>
            </div>

            {/* Search and Controls */}
            <div className="flex items-center gap-4 mb-6">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                    <Input
                        placeholder="Search contacts by name or email..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10"
                    />
                </div>

                <Button
                    onClick={() => {
                        // Simulate finding new duplicates
                        console.log('Scanning for duplicates...');
                    }}
                    variant="outline"
                    size="sm"
                >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Scan for Duplicates
                </Button>
            </div>

            {/* Duplicate Groups */}
            <div className="space-y-6">
                {filteredGroups.map((group) => (
                    <div
                        key={group.id}
                        className={`border rounded-lg p-4 ${selectedGroups.has(group.id) ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                            }`}
                    >
                        {/* Group Header */}
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-3">
                                <input
                                    type="checkbox"
                                    checked={selectedGroups.has(group.id)}
                                    onChange={() => handleGroupToggle(group.id)}
                                    className="w-4 h-4 text-blue-600"
                                />
                                <div>
                                    <h3 className="font-semibold text-gray-900">
                                        {group.contacts.length} Potential Duplicates
                                    </h3>
                                    <div className="flex items-center gap-2 text-sm text-gray-600">
                                        <span>Confidence: {Math.round(group.confidence * 100)}%</span>
                                        <span>•</span>
                                        <span>{group.reason}</span>
                                    </div>
                                </div>
                            </div>

                            <Badge variant={group.confidence > 0.9 ? "default" : "secondary"}>
                                {group.confidence > 0.9 ? 'High' : 'Medium'} Confidence
                            </Badge>
                        </div>

                        {/* Contact Comparison */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                            {group.contacts.map((contact, index) => (
                                <div
                                    key={contact.id}
                                    className={`p-4 border rounded-lg ${primaryContacts[group.id] === contact.id
                                            ? 'border-green-500 bg-green-50'
                                            : 'border-gray-200 bg-white'
                                        }`}
                                >
                                    {/* Contact Header */}
                                    <div className="flex items-start gap-3 mb-3">
                                        <input
                                            type="radio"
                                            name={`primary-${group.id}`}
                                            value={contact.id}
                                            checked={primaryContacts[group.id] === contact.id}
                                            onChange={() => handlePrimaryContactSelect(group.id, contact.id)}
                                            className="mt-1"
                                        />

                                        <div className="flex-1">
                                            <h4 className="font-medium text-gray-900">
                                                {contact.display_name || contact.email_address}
                                            </h4>
                                            <p className="text-sm text-gray-600">{contact.email_address}</p>

                                            {/* Source Services */}
                                            <div className="flex gap-1 mt-2">
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
                                    <div className="space-y-2 text-sm">
                                        <div className="flex justify-between">
                                            <span className="text-gray-600">Relevance Score:</span>
                                            <span className="font-medium">
                                                {Math.round((contact.relevance_score || 0) * 100)}%
                                            </span>
                                        </div>
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

                                        {contact.tags && contact.tags.length > 0 && (
                                            <div>
                                                <span className="text-gray-600">Tags:</span>
                                                <div className="flex flex-wrap gap-1 mt-1">
                                                    {contact.tags.map(tag => (
                                                        <Badge key={tag} variant="secondary" className="text-xs">
                                                            {tag}
                                                        </Badge>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {contact.notes && (
                                            <div>
                                                <span className="text-gray-600">Notes:</span>
                                                <p className="text-gray-900 mt-1 text-xs">{contact.notes}</p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Merge Notes */}
                        {selectedGroups.has(group.id) && (
                            <div className="mt-4">
                                <Label htmlFor={`notes-${group.id}`} className="text-sm font-medium text-gray-700">
                                    Merge Notes (Optional)
                                </Label>
                                <Textarea
                                    id={`notes-${group.id}`}
                                    placeholder="Add notes about this merge..."
                                    value={mergeNotes[group.id] || ''}
                                    onChange={(e) => handleMergeNotesChange(group.id, e.target.value)}
                                    rows={2}
                                    className="mt-1"
                                />
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {/* Merge Actions */}
            {selectedGroups.size > 0 && (
                <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <div className="flex items-center justify-between">
                        <div>
                            <h4 className="font-medium text-blue-900">
                                Ready to Merge {selectedGroups.size} Contact Group{selectedGroups.size > 1 ? 's' : ''}
                            </h4>
                            <p className="text-sm text-blue-700 mt-1">
                                Primary contacts have been selected. Secondary contacts will be merged into the primary ones.
                            </p>
                        </div>

                        <Button
                            onClick={handleMergeSelected}
                            disabled={!canMerge || isMerging}
                            className="flex items-center gap-2"
                        >
                            <Merge className="w-4 h-4" />
                            {isMerging ? 'Merging...' : `Merge ${selectedGroups.size} Group${selectedGroups.size > 1 ? 's' : ''}`}
                        </Button>
                    </div>
                </div>
            )}

            {/* Footer */}
            <div className="flex justify-end gap-3 pt-6 border-t border-gray-200 mt-6">
                <Button
                    onClick={onClose}
                    variant="outline"
                >
                    Close
                </Button>

                {duplicateGroups.length > 0 && (
                    <Button
                        onClick={() => {
                            // Mark all as not duplicates
                            setDuplicateGroups([]);
                        }}
                        variant="outline"
                    >
                        <X className="w-4 h-4 mr-2" />
                        Mark All as Not Duplicates
                    </Button>
                )}
            </div>
        </div>
    );
};

export default ContactMerger;
