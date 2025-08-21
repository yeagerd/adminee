/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type QuestionField = {
    /**
     * Unique identifier for the question
     */
    id?: string;
    /**
     * Display label for the question
     */
    label?: string;
    /**
     * Whether this question is required
     */
    required?: boolean;
    /**
     * Question type: text, email, textarea, select, phone, number
     */
    type?: string;
    /**
     * Options for select type questions
     */
    options?: (Array<string> | null);
    /**
     * Placeholder text for the input
     */
    placeholder?: (string | null);
    /**
     * Validation rule (e.g., email, phone, url)
     */
    validation?: (string | null);
};

