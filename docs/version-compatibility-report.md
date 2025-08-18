# API Version Compatibility Report

Generated: 2025-08-18T07:29:04.616975

## Summary

- **Total Services**: 5
- **Total Endpoints**: 85
- **Total Models**: 53

## Service Versions

### Shipments

- **Version**: 1.0.0-20250818
- **Title**: Shipments Service API
- **Endpoints**: 23
- **Models**: 18
- **Generated**: 2025-08-18T07:27:34.211977
- **Last Commit**: 0b0220b5

### Chat

- **Version**: 1.0.0-20250818
- **Title**: Chat Service API
- **Endpoints**: 13
- **Models**: 14
- **Generated**: 2025-08-18T07:27:34.230814
- **Last Commit**: 0b0220b5

### Vector_Db

- **Version**: 1.0.0-20250818
- **Title**: Vector_Db Service API
- **Endpoints**: 3
- **Models**: 0
- **Generated**: 2025-08-18T07:27:34.247114
- **Last Commit**: 0b0220b5

### Meetings

- **Version**: 1.0.0-20250818
- **Title**: Meetings Service API
- **Endpoints**: 43
- **Models**: 21
- **Generated**: 2025-08-18T07:27:34.263337
- **Last Commit**: 0b0220b5

### Email_Sync

- **Version**: 1.0.0-20250818
- **Title**: Email_Sync Service API
- **Endpoints**: 3
- **Models**: 0
- **Generated**: 2025-08-18T07:27:34.282434
- **Last Commit**: 0b0220b5

## Compatibility Matrix

| Service | Version | Status | Breaking Changes |
|---------|---------|--------|------------------|
| Shipments | 1.0.0-20250818 | ✅ Stable | None |
| Chat | 1.0.0-20250818 | ✅ Stable | None |
| Vector_Db | 1.0.0-20250818 | ✅ Stable | None |
| Meetings | 1.0.0-20250818 | ✅ Stable | None |
| Email_Sync | 1.0.0-20250818 | ✅ Stable | None |

## Endpoint Coverage

### Shipments (23 endpoints)

- `DELETE /v1/shipments/labels/{id}`
- `DELETE /v1/shipments/packages/{id}`
- `DELETE /v1/shipments/packages/{id}/labels/{label_id}`
- `DELETE /v1/shipments/packages/{package_id}/events/{event_id}`
- `GET /health`
- `GET /v1/shipments/carriers/`
- `GET /v1/shipments/events`
- `GET /v1/shipments/labels/`
- `GET /v1/shipments/packages`
- `GET /v1/shipments/packages/`
- `GET /v1/shipments/packages/collection-stats`
- `GET /v1/shipments/packages/{id}`
- `GET /v1/shipments/packages/{package_id}/events`
- `POST /v1/shipments/events/from-email`
- `POST /v1/shipments/labels/`
- `POST /v1/shipments/packages`
- `POST /v1/shipments/packages/`
- `POST /v1/shipments/packages/collect-data`
- `POST /v1/shipments/packages/{id}/labels`
- `POST /v1/shipments/packages/{id}/refresh`
- `POST /v1/shipments/packages/{package_id}/events`
- `PUT /v1/shipments/labels/{id}`
- `PUT /v1/shipments/packages/{id}`

### Chat (13 endpoints)

- `DELETE /v1/chat/drafts/{draft_id}`
- `GET /`
- `GET /health`
- `GET /ready`
- `GET /v1/chat/drafts`
- `GET /v1/chat/drafts/{draft_id}`
- `GET /v1/chat/threads`
- `GET /v1/chat/threads/{thread_id}/history`
- `POST /v1/chat/completions`
- `POST /v1/chat/completions/stream`
- `POST /v1/chat/drafts`
- `POST /v1/chat/feedback`
- `PUT /v1/chat/drafts/{draft_id}`

### Vector_Db (3 endpoints)

- `GET /`
- `GET /health`
- `GET /openapi.json`

### Meetings (43 endpoints)

- `DELETE /api/v1/bookings/one-time/{token}`
- `DELETE /api/v1/bookings/templates/{template_id}`
- `DELETE /api/v1/meetings/polls/{poll_id}`
- `DELETE /api/v1/meetings/polls/{poll_id}/slots/{slot_id}`
- `GET /`
- `GET /api/v1/bookings/health`
- `GET /api/v1/bookings/links`
- `GET /api/v1/bookings/links/{link_id}`
- `GET /api/v1/bookings/links/{link_id}/analytics`
- `GET /api/v1/bookings/links/{link_id}/one-time`
- `GET /api/v1/bookings/one-time/{token}`
- `GET /api/v1/bookings/public/{token}`
- `GET /api/v1/bookings/public/{token}/availability`
- `GET /api/v1/bookings/templates`
- `GET /api/v1/bookings/templates/{template_id}`
- `GET /api/v1/meetings/polls`
- `GET /api/v1/meetings/polls/`
- `GET /api/v1/meetings/polls/{poll_id}`
- `GET /api/v1/meetings/polls/{poll_id}/debug`
- `GET /api/v1/meetings/polls/{poll_id}/suggest-slots`
- `GET /api/v1/public/polls/response/{response_token}`
- `GET /health`
- `PATCH /api/v1/bookings/links/{link_id}`
- `PATCH /api/v1/bookings/one-time/{token}`
- `PATCH /api/v1/bookings/templates/{template_id}`
- `POST /api/v1/bookings/links`
- `POST /api/v1/bookings/links/{link_id}/duplicate`
- `POST /api/v1/bookings/links/{link_id}/one-time`
- `POST /api/v1/bookings/links/{link_id}/toggle`
- `POST /api/v1/bookings/public/{token}/book`
- `POST /api/v1/bookings/templates`
- `POST /api/v1/meetings/polls`
- `POST /api/v1/meetings/polls/`
- `POST /api/v1/meetings/polls/{poll_id}/participants`
- `POST /api/v1/meetings/polls/{poll_id}/participants/{participant_id}/resend-invitation`
- `POST /api/v1/meetings/polls/{poll_id}/schedule`
- `POST /api/v1/meetings/polls/{poll_id}/send-invitations/`
- `POST /api/v1/meetings/polls/{poll_id}/slots/`
- `POST /api/v1/meetings/polls/{poll_id}/unschedule`
- `POST /api/v1/meetings/process-email-response/`
- `PUT /api/v1/meetings/polls/{poll_id}`
- `PUT /api/v1/meetings/polls/{poll_id}/slots/{slot_id}`
- `PUT /api/v1/public/polls/response/{response_token}`

### Email_Sync (3 endpoints)

- `GET /`
- `GET /health`
- `GET /openapi.json`

## Model Coverage

### Shipments (18 models)

- `CarrierConfigOut`
- `DataCollectionRequest`
- `DataCollectionResponse`
- `EmailParseRequest`
- `EmailParseResponse`
- `HTTPValidationError`
- `LabelCreate`
- `LabelOut`
- `LabelUpdate`
- `PackageCreate`
- `PackageListResponse`
- `PackageOut`
- `PackageStatus`
- `PackageUpdate`
- `ParsedTrackingInfo`
- `TrackingEventCreate`
- `TrackingEventOut`
- `ValidationError`

### Chat (14 models)

- `ChatRequest`
- `ChatResponse`
- `DeleteUserDraftResponse`
- `DraftCalendarChange`
- `DraftCalendarEvent`
- `DraftEmail`
- `FeedbackRequest`
- `FeedbackResponse`
- `HTTPValidationError`
- `MessageResponse`
- `UserDraftListResponse`
- `UserDraftRequest`
- `UserDraftResponse`
- `ValidationError`

### Vector_Db (0 models)


### Meetings (21 models)

- `AvailabilityDataResponse`
- `AvailabilityResponse`
- `CreatePublicBookingRequest`
- `EmailResponseRequest`
- `HTTPValidationError`
- `MeetingPoll`
- `MeetingPollCreate`
- `MeetingPollUpdate`
- `MeetingType`
- `PollParticipant`
- `PollParticipantCreate`
- `PollResponse`
- `PollResponseCreate`
- `PollResponseTokenRequest`
- `PublicLinkDataResponse`
- `PublicLinkResponse`
- `QuestionField`
- `SuccessResponse`
- `TimeSlot`
- `TimeSlotCreate`
- `ValidationError`

### Email_Sync (0 models)


