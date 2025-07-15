import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { DraftMetadata, DraftType } from '@/types/draft';
import { Calendar, FileText, Mail } from 'lucide-react';

export interface DraftTemplate {
    id: string;
    name: string;
    description: string;
    type: DraftType;
    content: string;
    metadata: DraftMetadata;
}

const emailTemplates: DraftTemplate[] = [
    {
        id: 'email-follow-up',
        name: 'Follow-up Email',
        description: 'Professional follow-up after a meeting or conversation',
        type: 'email',
        content: 'Hi [Name],\n\nThank you for taking the time to [meet/discuss] with me today. I wanted to follow up on our conversation about [topic].\n\n[Key points from discussion]\n\nI look forward to [next steps].\n\nBest regards,\n[Your name]',
        metadata: {
            subject: 'Follow-up: [Topic]',
            recipients: [],
            priority: 'medium',
        },
    },
    {
        id: 'email-introduction',
        name: 'Introduction Email',
        description: 'Professional introduction to a new contact',
        type: 'email',
        content: 'Hi [Name],\n\nI hope this email finds you well. My name is [Your name] and I [brief introduction about yourself/your role].\n\nI came across your work on [topic/company] and was impressed by [specific detail]. I would love to connect and learn more about [shared interest/opportunity].\n\nWould you be available for a brief conversation?\n\nBest regards,\n[Your name]',
        metadata: {
            subject: 'Introduction - [Your name]',
            recipients: [],
            priority: 'medium',
        },
    },
];

const calendarTemplates: DraftTemplate[] = [
    {
        id: 'calendar-meeting',
        name: 'Team Meeting',
        description: 'Standard team meeting template',
        type: 'calendar',
        content: 'Weekly team meeting to discuss:\n\n- Project updates\n- Blockers and challenges\n- Next week priorities\n- Open discussion',
        metadata: {
            title: 'Team Meeting',
            startTime: (() => new Date().toISOString()) as string | (() => string),
            endTime: (() => new Date(Date.now() + 3600000).toISOString()) as string | (() => string),
            attendees: [],
            priority: 'medium',
        },
    },
    {
        id: 'calendar-review',
        name: '1:1 Review',
        description: 'One-on-one review meeting',
        type: 'calendar',
        content: '1:1 meeting agenda:\n\n- Progress review\n- Goals and objectives\n- Feedback and development\n- Action items',
        metadata: {
            title: '1:1 Review',
            startTime: (() => new Date().toISOString()) as string | (() => string),
            endTime: (() => new Date(Date.now() + 1800000).toISOString()) as string | (() => string),
            attendees: [],
            priority: 'high',
        },
    },
];

const documentTemplates: DraftTemplate[] = [
    {
        id: 'document-meeting-notes',
        name: 'Meeting Notes',
        description: 'Template for meeting notes and action items',
        type: 'document',
        content: '# Meeting Notes\n\n**Date:** [Date]\n**Attendees:** [List of attendees]\n**Agenda:** [Meeting agenda]\n\n## Discussion Points\n\n[Key discussion points]\n\n## Action Items\n\n- [ ] [Action item 1] - [Assignee] - [Due date]\n- [ ] [Action item 2] - [Assignee] - [Due date]\n\n## Next Steps\n\n[Next steps and follow-up items]',
        metadata: {
            title: 'Meeting Notes - [Topic]',
            tags: ['meeting', 'notes'],
            priority: 'medium',
        },
    },
    {
        id: 'document-proposal',
        name: 'Project Proposal',
        description: 'Template for project proposals',
        type: 'document',
        content: '# Project Proposal: [Project Name]\n\n## Executive Summary\n\n[Brief overview of the project]\n\n## Problem Statement\n\n[Description of the problem being solved]\n\n## Proposed Solution\n\n[Detailed description of the solution]\n\n## Timeline\n\n[Project timeline and milestones]\n\n## Budget\n\n[Budget breakdown]\n\n## Success Metrics\n\n[How success will be measured]',
        metadata: {
            title: 'Project Proposal: [Project Name]',
            tags: ['proposal', 'project'],
            priority: 'high',
        },
    },
];

interface DraftTemplatesProps {
    type: DraftType;
    onSelectTemplate: (template: DraftTemplate) => void;
}

export function DraftTemplates({ type, onSelectTemplate }: DraftTemplatesProps) {
    const getTemplates = () => {
        switch (type) {
            case 'email':
                return emailTemplates;
            case 'calendar':
                return calendarTemplates;
            case 'document':
                return documentTemplates;
            default:
                return [];
        }
    };

    const getIcon = () => {
        switch (type) {
            case 'email':
                return <Mail className="h-5 w-5" />;
            case 'calendar':
                return <Calendar className="h-5 w-5" />;
            case 'document':
                return <FileText className="h-5 w-5" />;
        }
    };

    const templates = getTemplates();

    const handleSelectTemplate = (template: DraftTemplate) => {
        // If calendar, resolve dynamic startTime/endTime
        if (template.type === 'calendar') {
            const metadata = { ...template.metadata };
            const startTime = metadata.startTime;
            const endTime = metadata.endTime;
            metadata.startTime = typeof startTime === 'function' ? startTime() : startTime;
            metadata.endTime = typeof endTime === 'function' ? endTime() : endTime;
            onSelectTemplate({ ...template, metadata });
        } else {
            onSelectTemplate(template);
        }
    };

    if (templates.length === 0) {
        return (
            <div className="text-center text-muted-foreground py-8">
                No templates available for this draft type.
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center gap-2">
                {getIcon()}
                <h3 className="text-lg font-semibold">Templates</h3>
            </div>

            <div className="grid gap-4">
                {templates.map((template) => (
                    <Card key={template.id} className="cursor-pointer hover:shadow-md transition-shadow">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-base">{template.name}</CardTitle>
                            <CardDescription>{template.description}</CardDescription>
                        </CardHeader>
                        <CardContent className="pt-0">
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleSelectTemplate(template)}
                                className="w-full"
                            >
                                Use Template
                            </Button>
                        </CardContent>
                    </Card>
                ))}
            </div>
        </div>
    );
} 