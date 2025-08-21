/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MeetingType } from './MeetingType';
import type { PollParticipant } from './PollParticipant';
import type { PollResponse } from './PollResponse';
import type { TimeSlot } from './TimeSlot';
export type MeetingPoll = {
    title: string;
    description: (string | null);
    duration_minutes: number;
    location: (string | null);
    meeting_type: MeetingType;
    response_deadline: (string | null);
    min_participants?: (number | null);
    max_participants?: (number | null);
    reveal_participants?: (boolean | null);
    send_emails?: (boolean | null);
    id: string;
    user_id: string;
    status: string;
    created_at: string;
    updated_at: string;
    poll_token: string;
    time_slots: Array<TimeSlot>;
    participants: Array<PollParticipant>;
    responses?: (Array<PollResponse> | null);
    scheduled_slot_id?: (string | null);
    calendar_event_id?: (string | null);
};

