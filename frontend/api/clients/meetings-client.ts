import { 
    MeetingPoll,
    MeetingPollCreate,
    MeetingPollUpdate,
    PollResponse,
    TimeSlot,
    PollParticipant,
    TimeSlotCreate,
    PollParticipantCreate,
    SuccessResponse
} from '../../types/api/meetings';
import { GatewayClient } from './gateway-client';

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

    async scheduleMeeting(pollId: string, selectedSlotId: string): Promise<SuccessResponse<{ event_id?: string; status: string; provider: string }>> {
        return this.request<SuccessResponse<{ event_id?: string; status: string; provider: string }>>(`/api/v1/meetings/polls/${pollId}/schedule`, {
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

    async unscheduleMeeting(pollId: string): Promise<SuccessResponse<{ status?: string }>> {
        return this.request<SuccessResponse<{ status?: string }>>(`/api/v1/meetings/polls/${pollId}/unschedule`, {
            method: 'POST',
        });
    }
}
