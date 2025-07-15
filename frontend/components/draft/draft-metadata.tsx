'use client';

import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { DraftMetadataProps } from '@/types/draft';

export function DraftMetadata({ draft, onUpdate, type }: DraftMetadataProps) {
    const handleMetadataChange = (key: string, value: string | string[]) => {
        onUpdate({ [key]: value });
    };

    const renderEmailMetadata = () => (
        <div className="space-y-4">
            <div className="space-y-2">
                <Label htmlFor="subject">Subject</Label>
                <Input
                    id="subject"
                    value={draft.metadata.subject || ''}
                    onChange={(e) => handleMetadataChange('subject', e.target.value)}
                    placeholder="Enter email subject..."
                    className="w-full"
                />
            </div>

            <div className="space-y-2">
                <Label htmlFor="recipients">To</Label>
                <Input
                    id="recipients"
                    value={draft.metadata.recipients?.join(', ') || ''}
                    onChange={(e) => handleMetadataChange('recipients', e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                    placeholder="recipient@example.com, another@example.com"
                    className="w-full"
                />
            </div>

            <div className="space-y-2">
                <Label htmlFor="cc">CC</Label>
                <Input
                    id="cc"
                    value={draft.metadata.cc?.join(', ') || ''}
                    onChange={(e) => handleMetadataChange('cc', e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                    placeholder="cc@example.com"
                    className="w-full"
                />
            </div>

            <div className="space-y-2">
                <Label htmlFor="bcc">BCC</Label>
                <Input
                    id="bcc"
                    value={draft.metadata.bcc?.join(', ') || ''}
                    onChange={(e) => handleMetadataChange('bcc', e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                    placeholder="bcc@example.com"
                    className="w-full"
                />
            </div>
        </div>
    );

    const renderCalendarMetadata = () => (
        <div className="space-y-4">
            <div className="space-y-2">
                <Label htmlFor="title">Event Title</Label>
                <Input
                    id="title"
                    value={draft.metadata.title || ''}
                    onChange={(e) => handleMetadataChange('title', e.target.value)}
                    placeholder="Enter event title..."
                    className="w-full"
                />
            </div>

            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                    <Label htmlFor="startTime">Start Time</Label>
                    <Input
                        id="startTime"
                        type="datetime-local"
                        value={typeof draft.metadata.startTime === 'function' ? draft.metadata.startTime() : draft.metadata.startTime || ''}
                        onChange={(e) => handleMetadataChange('startTime', e.target.value)}
                        className="w-full"
                    />
                </div>

                <div className="space-y-2">
                    <Label htmlFor="endTime">End Time</Label>
                    <Input
                        id="endTime"
                        type="datetime-local"
                        value={typeof draft.metadata.endTime === 'function' ? draft.metadata.endTime() : draft.metadata.endTime || ''}
                        onChange={(e) => handleMetadataChange('endTime', e.target.value)}
                        className="w-full"
                    />
                </div>
            </div>

            <div className="space-y-2">
                <Label htmlFor="location">Location</Label>
                <Input
                    id="location"
                    value={draft.metadata.location || ''}
                    onChange={(e) => handleMetadataChange('location', e.target.value)}
                    placeholder="Enter location..."
                    className="w-full"
                />
            </div>

            <div className="space-y-2">
                <Label htmlFor="attendees">Attendees</Label>
                <Input
                    id="attendees"
                    value={draft.metadata.attendees?.join(', ') || ''}
                    onChange={(e) => handleMetadataChange('attendees', e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                    placeholder="attendee@example.com, another@example.com"
                    className="w-full"
                />
            </div>
        </div>
    );

    const renderDocumentMetadata = () => (
        <div className="space-y-4">
            <div className="space-y-2">
                <Label htmlFor="docTitle">Document Title</Label>
                <Input
                    id="docTitle"
                    value={draft.metadata.title || ''}
                    onChange={(e) => handleMetadataChange('title', e.target.value)}
                    placeholder="Enter document title..."
                    className="w-full"
                />
            </div>

            <div className="space-y-2">
                <Label htmlFor="tags">Tags</Label>
                <Input
                    id="tags"
                    value={draft.metadata.tags?.join(', ') || ''}
                    onChange={(e) => handleMetadataChange('tags', e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                    placeholder="tag1, tag2, tag3"
                    className="w-full"
                />
            </div>

            <div className="space-y-2">
                <Label htmlFor="priority">Priority</Label>
                <Select
                    value={draft.metadata.priority || 'medium'}
                    onValueChange={(value) => handleMetadataChange('priority', value)}
                >
                    <SelectTrigger>
                        <SelectValue placeholder="Select priority" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="low">Low</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="high">High</SelectItem>
                    </SelectContent>
                </Select>
            </div>
        </div>
    );

    const renderMetadataByType = () => {
        switch (type) {
            case 'email':
                return renderEmailMetadata();
            case 'calendar':
                return renderCalendarMetadata();
            case 'document':
                return renderDocumentMetadata();
            default:
                return null;
        }
    };

    return (
        <div className="p-4 border-b bg-muted/30">
            <h3 className="text-sm font-medium text-muted-foreground mb-4">
                {type.charAt(0).toUpperCase() + type.slice(1)} Details
            </h3>
            {renderMetadataByType()}
        </div>
    );
} 