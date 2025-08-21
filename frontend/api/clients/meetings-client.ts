import {
    MeetingPoll,
    MeetingPollCreate,
    MeetingPollUpdate,
    PollParticipant,
    PollResponseTokenRequest,
    SuccessResponse
} from '../../types/api/meetings';
import { GatewayClient } from './gateway-client';

export class MeetingsClient extends GatewayClient {
    // Public polls service
    async getPollResponse(responseToken: string): Promise<MeetingPoll> {
        return this.request<MeetingPoll>(`/api/v1/public/polls/response/${responseToken}`);
    }

    async updatePollResponse(responseToken: string, requestBody: PollResponseTokenRequest): Promise<SuccessResponse> {
        return this.request<SuccessResponse>(`/api/v1/public/polls/response/${responseToken}`, {
            method: 'PUT',
            body: requestBody,
        });
    }

    // Meetings Service
    async listMeetingPolls(): Promise<MeetingPoll[]> {
        return this.request<MeetingPoll[]>('/api/v1/meetings/polls');
    }

    async getMeetingPoll(pollId: string): Promise<MeetingPoll> {
        return this.request<MeetingPoll>(`/api/v1/meetings/polls/${pollId}`);
    }

    async createMeetingPoll(pollData: MeetingPollCreate): Promise<MeetingPoll> {
        // Handle null values properly for the API
        const apiData = {
            title: pollData.title,
            description: pollData.description,
            duration_minutes: pollData.duration_minutes,
            location: pollData.location,
            meeting_type: pollData.meeting_type,
            response_deadline: pollData.response_deadline,
            min_participants: pollData.min_participants,
            max_participants: pollData.max_participants,
            reveal_participants: pollData.reveal_participants,
            send_emails: pollData.send_emails,
            time_slots: pollData.time_slots,
            participants: pollData.participants,
        };

        return this.request<MeetingPoll>('/api/v1/meetings/polls', {
            method: 'POST',
            body: apiData,
        });
    }

    async updateMeetingPoll(pollId: string, pollData: MeetingPollUpdate): Promise<MeetingPoll> {
        // Handle null values properly for the API
        const apiData = {
            title: pollData.title,
            description: pollData.description,
            duration_minutes: pollData.duration_minutes,
            location: pollData.location,
            meeting_type: pollData.meeting_type,
            response_deadline: pollData.response_deadline,
            min_participants: pollData.min_participants,
            max_participants: pollData.max_participants,
            reveal_participants: pollData.reveal_participants,
        };

        return this.request<MeetingPoll>(`/api/v1/meetings/polls/${pollId}`, {
            method: 'PUT',
            body: apiData,
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

    async scheduleMeeting(pollId: string, selectedSlotId: string): Promise<SuccessResponse> {
        return this.request<SuccessResponse>(`/api/v1/meetings/polls/${pollId}/schedule`, {
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

    async unscheduleMeeting(pollId: string): Promise<SuccessResponse> {
        return this.request<SuccessResponse>(`/api/v1/meetings/polls/${pollId}/unschedule`, {
            method: 'POST',
        });
    }
}
