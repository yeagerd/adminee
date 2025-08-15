import { ApiResponse } from '../types/common';
import { GatewayClient } from './gateway-client';

// Meeting Poll Types
export interface MeetingPoll {
    id: string;
    user_id: string;
    title: string;
    description?: string;
    duration_minutes: number;
    location?: string;
    meeting_type: string;
    response_deadline?: string;
    min_participants?: number;
    max_participants?: number;
    reveal_participants?: boolean;
    status: string;
    created_at: string;
    updated_at: string;
    poll_token: string;
    time_slots: TimeSlot[];
    participants: PollParticipant[];
    responses?: PollResponse[];
    scheduled_slot_id?: string;
    calendar_event_id?: string;
}

export interface PollResponse {
    id: string;
    participant_id: string;
    time_slot_id: string;
    response: string;
    comment?: string;
    created_at: string;
    updated_at: string;
}

export interface TimeSlot {
    id: string;
    start_time: string;
    end_time: string;
    timezone: string;
    is_available: boolean;
}

export interface PollParticipant {
    id: string;
    email: string;
    name?: string;
    status: string;
    invited_at: string;
    responded_at?: string;
    reminder_sent_count: number;
    response_token: string;
}

export interface MeetingPollCreate {
    title: string;
    description?: string;
    duration_minutes: number;
    location?: string;
    meeting_type: string;
    response_deadline?: string;
    min_participants?: number;
    max_participants?: number;
    reveal_participants?: boolean;
    time_slots: TimeSlotCreate[];
    participants: PollParticipantCreate[];
}

export interface TimeSlotCreate {
    start_time: string;
    end_time: string;
    timezone: string;
}

export interface PollParticipantCreate {
    email: string;
    name?: string;
    poll_id?: string;
    response_token?: string;
}

export interface MeetingPollUpdate {
    title?: string;
    description?: string;
    duration_minutes?: number;
    location?: string;
    meeting_type?: string;
    response_deadline?: string;
    min_participants?: number;
    max_participants?: number;
}

export class MeetingsClient extends GatewayClient {
    // Meetings Service
    async listMeetingPolls(): Promise<MeetingPoll[]> {
        return this.request<MeetingPoll[]>('/api/v1/meetings/polls');
    }

    async getMeetingPoll(pollId: string): Promise<MeetingPoll> {
        return this.request<MeetingPoll>(`/api/v1/meetings/polls/${pollId}`);
    }

    async createMeetingPoll(pollData: MeetingPollCreate): Promise<MeetingPoll> {
        const normalized: MeetingPollCreate = {
            ...pollData,
            response_deadline: this.normalizeDate(pollData.response_deadline),
        };
        return this.request<MeetingPoll>('/api/v1/meetings/polls', {
            method: 'POST',
            body: normalized,
        });
    }

    async updateMeetingPoll(pollId: string, pollData: MeetingPollUpdate): Promise<MeetingPoll> {
        const normalized: MeetingPollUpdate = {
            ...pollData,
            response_deadline: this.normalizeDate(pollData.response_deadline),
        };
        return this.request<MeetingPoll>(`/api/v1/meetings/polls/${pollId}`, {
            method: 'PUT',
            body: normalized,
        });
    }

    async deleteMeetingPoll(pollId: string): Promise<void> {
        return this.request<void>(`/api/v1/meetings/polls/${pollId}`, {
            method: 'DELETE',
        });
    }

    async sendMeetingInvitations(pollId: string): Promise<void> {
        return this.request<void>(`/api/v1/meetings/polls/${pollId}/send-invitations`, {
            method: 'POST',
        });
    }

    async resendMeetingInvitation(pollId: string, participantId: string): Promise<void> {
        return this.request<void>(`/api/v1/meetings/polls/${pollId}/participants/${participantId}/resend-invitation`, {
            method: 'POST',
        });
    }

    async scheduleMeeting(pollId: string, selectedSlotId: string): Promise<ApiResponse<{ event_id?: string; status: string; provider: string }>> {
        return this.request<ApiResponse<{ event_id?: string; status: string; provider: string }>>(`/api/v1/meetings/polls/${pollId}/schedule`, {
            method: 'POST',
            body: { selectedSlotId },
        });
    }

    async addMeetingParticipant(pollId: string, email: string, name: string): Promise<PollParticipant> {
        return this.request<PollParticipant>(`/api/v1/meetings/polls/${pollId}/participants`, {
            method: 'POST',
            body: { email, name },
        });
    }

    async unscheduleMeeting(pollId: string): Promise<ApiResponse<{ status?: string }>> {
        return this.request<ApiResponse<{ status?: string }>>(`/api/v1/meetings/polls/${pollId}/unschedule`, {
            method: 'POST',
        });
    }
}
