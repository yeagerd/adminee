/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MeetingType } from './MeetingType';
import type { PollParticipantCreate } from './PollParticipantCreate';
import type { TimeSlotCreate } from './TimeSlotCreate';
export type MeetingPollCreate = {
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
    time_slots: Array<TimeSlotCreate>;
    participants: Array<PollParticipantCreate>;
};

