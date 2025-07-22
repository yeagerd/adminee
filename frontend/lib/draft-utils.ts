import { Draft, DraftMetadata, DraftType } from '@/types/draft';
import { DraftData, DraftEmail, DraftCalendarEvent, DraftCalendarChange } from '@/components/chat-interface';

export function formatDraftDate(date: string): string {
    return new Date(date).toLocaleString();
}

export function filterDraftsBySearch(drafts: Draft[], search: string): Draft[] {
    if (!search) return drafts;
    return drafts.filter((draft: Draft) =>
        draft.content?.toLowerCase().includes(search.toLowerCase()) ||
        draft.metadata?.subject?.toLowerCase().includes(search.toLowerCase())
    );
}

export function sortDraftsByUpdated(drafts: Draft[]): Draft[] {
    return [...drafts].sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
}

export function convertDraftDataToDraft(draftData: DraftData, userId: string): Draft {
    let content = '';
    let metadata: DraftMetadata = {};

    if (draftData.type === 'email') {
        const emailData = draftData as DraftEmail;
        content = emailData.body || '';
        metadata = {
            subject: emailData.subject,
            recipients: emailData.to ? [emailData.to] : [],
            cc: emailData.cc,
            bcc: emailData.bcc ? [emailData.bcc] : [],
        };
    } else if (draftData.type === 'calendar_event') {
        const eventData = draftData as DraftCalendarEvent;
        content = eventData.description || '';
        metadata = {
            title: eventData.title,
            startTime: eventData.start_time,
            endTime: eventData.end_time,
            location: eventData.location,
            attendees: eventData.attendees,
        };
    } else if (draftData.type === 'calendar_change') {
        const changeData = draftData as DraftCalendarChange;
        content = changeData.new_description || '';
        metadata = {
            title: changeData.new_title,
            startTime: changeData.new_start_time,
            endTime: changeData.new_end_time,
            location: changeData.new_location,
            attendees: changeData.new_attendees,
        };
    }

    return {
        id: `draft_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        type: draftData.type as DraftType,
        status: 'draft',
        content,
        metadata,
        isAIGenerated: true,
        createdAt: draftData.created_at,
        updatedAt: draftData.updated_at || draftData.created_at,
        userId,
    };
}