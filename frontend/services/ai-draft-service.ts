import { gatewayClient } from '@/lib/gateway-client';
import { Draft, DraftType } from '@/types/draft';

export interface AIDraftRequest {
    type: DraftType;
    prompt: string;
    context?: string;
    metadata?: Record<string, unknown>;
    threadId?: string;
}

export interface AIDraftSuggestion {
    id: string;
    type: 'improvement' | 'correction' | 'expansion' | 'formatting';
    title: string;
    description: string;
    content?: string;
    confidence: number;
}

export interface AIDraftResponse {
    draft: Draft;
    suggestions: AIDraftSuggestion[];
    confidence: number;
    reasoning?: string;
}

export class AIDraftService {
    async generateDraft(request: AIDraftRequest): Promise<AIDraftResponse> {
        try {
            // Use the chat service to generate a draft
            const response = await gatewayClient.chat(
                `Generate a ${request.type} draft based on this prompt: ${request.prompt}${request.context ? `\n\nContext: ${request.context}` : ''}`,
                request.threadId
            );

            // Parse the AI response to extract draft content and metadata
            const draftContent = this.extractDraftContent(response);
            const draftMetadata = this.extractDraftMetadata(response, request.type);

            // Create the draft through the regular draft service
            const draft = await gatewayClient.createDraft({
                type: request.type as string,
                content: draftContent,
                metadata: {
                    ...draftMetadata,
                    ...request.metadata,
                    ai_generated: true,
                    ai_prompt: request.prompt,
                    ai_context: request.context,
                },
                threadId: request.threadId,
            });

            // Generate suggestions for improvements
            const suggestions = await this.generateSuggestions(draft, request.prompt);

            return {
                draft: this.mapDraftFromApi(draft),
                suggestions,
                confidence: this.calculateConfidence(response),
                reasoning: this.extractReasoning(response),
            };
        } catch (error) {
            throw new Error(`Failed to generate AI draft: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async improveDraft(draftId: string, improvementPrompt: string): Promise<AIDraftResponse> {
        try {
            // Get the current draft
            const currentDraft = await gatewayClient.getDraft(draftId);

            // Ask AI to improve the draft
            const response = await gatewayClient.chat(
                `Improve this ${currentDraft.type} draft based on this request: ${improvementPrompt}\n\nCurrent draft:\n${currentDraft.content}`,
                currentDraft.thread_id
            );

            // Extract improved content
            const improvedContent = this.extractDraftContent(response);
            const improvedMetadata = this.extractDraftMetadata(response, currentDraft.type as DraftType);

            // Update the draft
            const updatedDraft = await gatewayClient.updateDraft(draftId, {
                content: improvedContent,
                metadata: {
                    ...currentDraft.metadata,
                    ...improvedMetadata,
                    ai_improved: true,
                    ai_improvement_prompt: improvementPrompt,
                },
            });

            // Generate new suggestions
            const suggestions = await this.generateSuggestions(updatedDraft, improvementPrompt);

            return {
                draft: this.mapDraftFromApi(updatedDraft),
                suggestions,
                confidence: this.calculateConfidence(response),
                reasoning: this.extractReasoning(response),
            };
        } catch (error) {
            throw new Error(`Failed to improve draft: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async generateSuggestions(draft: any, context?: string): Promise<AIDraftSuggestion[]> {
        try {
            const response = await gatewayClient.chat(
                `Analyze this ${draft.type} draft and provide specific suggestions for improvement. Focus on clarity, tone, structure, and any missing information.\n\nDraft:\n${draft.content}${context ? `\n\nContext: ${context}` : ''}`,
                draft.thread_id
            );

            return this.parseSuggestions(response);
        } catch (error) {
            console.warn('Failed to generate suggestions:', error);
            return [];
        }
    }

    async approveAIDraft(draftId: string): Promise<void> {
        await gatewayClient.updateDraft(draftId, {
            metadata: { ai_status: 'approved' },
        });
    }

    async rejectAIDraft(draftId: string, reason?: string): Promise<void> {
        await gatewayClient.updateDraft(draftId, {
            metadata: {
                ai_status: 'rejected',
                ai_rejection_reason: reason,
            },
        });
    }

    private extractDraftContent(aiResponse: any): string {
        // Extract the main content from AI response
        // This is a simplified implementation - in practice, you'd want more sophisticated parsing
        if (typeof aiResponse === 'string') {
            return aiResponse;
        }

        if (aiResponse.content) {
            return aiResponse.content;
        }

        if (aiResponse.message) {
            return aiResponse.message;
        }

        return JSON.stringify(aiResponse);
    }

    private extractDraftMetadata(aiResponse: any, type: DraftType): Record<string, unknown> {
        const metadata: Record<string, unknown> = {};

        // Extract type-specific metadata based on AI response
        if (type === 'email') {
            metadata.subject = this.extractEmailSubject(aiResponse);
            metadata.recipients = this.extractEmailRecipients(aiResponse);
        } else if (type === 'calendar') {
            metadata.title = this.extractCalendarTitle(aiResponse);
            metadata.startTime = this.extractCalendarStartTime(aiResponse);
            metadata.endTime = this.extractCalendarEndTime(aiResponse);
        } else if (type === 'document') {
            metadata.title = this.extractDocumentTitle(aiResponse);
        }

        return metadata;
    }

    private extractEmailSubject(response: any): string {
        // Extract email subject from AI response
        const content = typeof response === 'string' ? response : JSON.stringify(response);
        const subjectMatch = content.match(/subject[:\s]+([^\n]+)/i);
        return subjectMatch ? subjectMatch[1].trim() : 'No Subject';
    }

    private extractEmailRecipients(response: any): string[] {
        // Extract email recipients from AI response
        const content = typeof response === 'string' ? response : JSON.stringify(response);
        const recipientMatch = content.match(/to[:\s]+([^\n]+)/i);
        if (recipientMatch) {
            return recipientMatch[1].split(',').map((r: string) => r.trim());
        }
        return [];
    }

    private extractCalendarTitle(response: any): string {
        // Extract calendar event title from AI response
        const content = typeof response === 'string' ? response : JSON.stringify(response);
        const titleMatch = content.match(/title[:\s]+([^\n]+)/i);
        return titleMatch ? titleMatch[1].trim() : 'New Event';
    }

    private extractCalendarStartTime(response: any): string {
        // Extract calendar start time from AI response
        const content = typeof response === 'string' ? response : JSON.stringify(response);
        const startMatch = content.match(/start[:\s]+([^\n]+)/i);
        return startMatch ? startMatch[1].trim() : new Date().toISOString();
    }

    private extractCalendarEndTime(response: any): string {
        // Extract calendar end time from AI response
        const content = typeof response === 'string' ? response : JSON.stringify(response);
        const endMatch = content.match(/end[:\s]+([^\n]+)/i);
        return endMatch ? endMatch[1].trim() : new Date(Date.now() + 3600000).toISOString();
    }

    private extractDocumentTitle(response: any): string {
        // Extract document title from AI response
        const content = typeof response === 'string' ? response : JSON.stringify(response);
        const titleMatch = content.match(/title[:\s]+([^\n]+)/i);
        return titleMatch ? titleMatch[1].trim() : 'Untitled Document';
    }

    private parseSuggestions(aiResponse: any): AIDraftSuggestion[] {
        // Parse AI suggestions from response
        // This is a simplified implementation
        const suggestions: AIDraftSuggestion[] = [];

        try {
            const content = typeof aiResponse === 'string' ? aiResponse : JSON.stringify(aiResponse);

            // Look for suggestion patterns in the AI response
            const suggestionMatches = content.match(/suggestion[:\s]+([^\n]+)/gi);
            if (suggestionMatches) {
                suggestionMatches.forEach((match: string, index: number) => {
                    const description = match.replace(/suggestion[:\s]+/i, '').trim();
                    suggestions.push({
                        id: `suggestion-${index}`,
                        type: 'improvement',
                        title: `Suggestion ${index + 1}`,
                        description,
                        confidence: 0.8,
                    });
                });
            }
        } catch (error) {
            console.warn('Failed to parse suggestions:', error);
        }

        return suggestions;
    }

    private calculateConfidence(aiResponse: any): number {
        // Calculate confidence score based on AI response
        // This is a simplified implementation
        const content = typeof aiResponse === 'string' ? aiResponse : JSON.stringify(aiResponse);

        // Simple heuristics for confidence calculation
        let confidence = 0.7; // Base confidence

        if (content.length > 100) confidence += 0.1;
        if (content.includes('subject') || content.includes('title')) confidence += 0.1;
        if (content.includes('dear') || content.includes('hello')) confidence += 0.1;

        return Math.min(confidence, 1.0);
    }

    private extractReasoning(aiResponse: any): string {
        // Extract AI reasoning from response
        const content = typeof aiResponse === 'string' ? aiResponse : JSON.stringify(aiResponse);
        const reasoningMatch = content.match(/reasoning[:\s]+([^\n]+)/i);
        return reasoningMatch ? reasoningMatch[1].trim() : '';
    }

    private mapDraftFromApi(apiDraft: any): Draft {
        return {
            id: apiDraft.id,
            type: apiDraft.type as DraftType,
            status: apiDraft.status,
            content: apiDraft.content,
            metadata: apiDraft.metadata,
            isAIGenerated: apiDraft.is_ai_generated ?? false,
            createdAt: apiDraft.created_at,
            updatedAt: apiDraft.updated_at,
            userId: apiDraft.user_id,
            threadId: apiDraft.thread_id,
        };
    }
}

// Default AI draft service instance
export const aiDraftService = new AIDraftService(); 