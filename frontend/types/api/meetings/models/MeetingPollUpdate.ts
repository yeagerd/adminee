/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MeetingType } from './MeetingType';
export type MeetingPollUpdate = {
    title?: (string | null);
    description?: (string | null);
    duration_minutes?: (number | null);
    location?: (string | null);
    meeting_type?: (MeetingType | null);
    response_deadline?: (string | null);
    min_participants?: (number | null);
    max_participants?: (number | null);
    reveal_participants?: (boolean | null);
};

