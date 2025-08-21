/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AIModelProvider } from './AIModelProvider';
import type { AIModelType } from './AIModelType';
/**
 * AI preferences schema.
 */
export type AIPreferencesSchema = {
    /**
     * Preferred AI provider
     */
    preferred_provider?: AIModelProvider;
    /**
     * Preferred AI model
     */
    preferred_model?: AIModelType;
    /**
     * AI response style preference
     */
    response_style?: string;
    /**
     * Preferred response length
     */
    response_length?: string;
    /**
     * Enable automatic summarization
     */
    auto_summarization?: boolean;
    /**
     * Enable smart suggestions
     */
    smart_suggestions?: boolean;
    /**
     * Enable context-aware responses
     */
    context_awareness?: boolean;
    /**
     * AI creativity/randomness level
     */
    temperature?: number;
    /**
     * Maximum tokens per response
     */
    max_tokens?: number;
};

