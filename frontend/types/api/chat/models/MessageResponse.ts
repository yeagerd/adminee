/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * API response model for chat messages.
 *
 * This is the API/serialization representation of a chat message, separate from
 * the database Message model to maintain clean separation of concerns.
 *
 * Note: This model is separate from Message (database model) to maintain
 * clean separation between data persistence and API contracts.
 *
 * API Design:
 * - Uses string types for JSON serialization compatibility
 * - Adds computed fields not present in database (llm_generated)
 * - Excludes internal database relationships (thread)
 * - Provides stable API contract independent of database schema
 * - Uses descriptive field names (message_id vs id)
 *
 * Database Conversion:
 * - Created by converting Message database model in API layer
 * - ID fields converted from int to string for JSON compatibility
 * - Datetime fields converted to string for JSON serialization
 * - Computed fields added based on business logic
 * - Relationships excluded for clean API response
 *
 * Example conversion from Message database model:
 * MessageResponse(
     * message_id=str(message.id),         # int -> str, renamed
     * thread_id=str(message.thread_id),   # int -> str
     * user_id=message.user_id,
     * llm_generated=(message.user_id != user_id),  # computed field
     * content=message.content,
     * created_at=str(message.created_at), # datetime -> str
     * )
     */
    export type MessageResponse = {
        message_id: string;
        thread_id: string;
        user_id: string;
        llm_generated?: boolean;
        content: string;
        created_at: string;
    };

