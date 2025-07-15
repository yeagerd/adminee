import { AIDraftSuggestion } from '@/services/ai-draft-service';
import { Draft, DraftType } from '@/types/draft';

export interface AIDraftHandoffData {
    draftId: string;
    originalContent: string;
    aiContent: string;
    suggestions: AIDraftSuggestion[];
    confidence: number;
    handoffReason: string;
}

export interface AIDraftAnalytics {
    totalGenerated: number;
    totalApproved: number;
    totalRejected: number;
    totalModified: number;
    averageConfidence: number;
    mostUsedType: DraftType;
    suggestionsApplied: number;
}

export class AIDraftIntegration {
    /**
     * Determines if a draft should be handed off from AI to user
     */
    static shouldHandoffToUser(
        draft: Draft,
        confidence: number,
        suggestions: AIDraftSuggestion[]
    ): boolean {
        // Handoff if confidence is low
        if (confidence < 0.6) {
            return true;
        }

        // Handoff if there are critical corrections needed
        const hasCriticalCorrections = suggestions.some(
            suggestion => suggestion.type === 'correction' && suggestion.confidence > 0.8
        );
        if (hasCriticalCorrections) {
            return true;
        }

        // Handoff if content is too short or incomplete
        if (draft.content.length < 50) {
            return true;
        }

        // Handoff if metadata is missing critical fields
        if (this.isMissingCriticalMetadata(draft)) {
            return true;
        }

        return false;
    }

    /**
     * Checks if draft is missing critical metadata for its type
     */
    private static isMissingCriticalMetadata(draft: Draft): boolean {
        switch (draft.type) {
            case 'email':
                return !draft.metadata.subject || !draft.metadata.recipients?.length;
            case 'calendar':
                return !draft.metadata.title || !draft.metadata.startTime;
            case 'document':
                return !draft.metadata.title;
            default:
                return false;
        }
    }

    /**
     * Merges AI suggestions with existing draft content
     */
    static mergeSuggestionsWithContent(
        originalContent: string,
        suggestions: AIDraftSuggestion[]
    ): string {
        let mergedContent = originalContent;

        // Sort suggestions by type priority
        const sortedSuggestions = suggestions.sort((a, b) => {
            const priorityOrder = { correction: 0, formatting: 1, improvement: 2, expansion: 3 };
            return (priorityOrder[a.type] || 0) - (priorityOrder[b.type] || 0);
        });

        for (const suggestion of sortedSuggestions) {
            if (suggestion.content) {
                switch (suggestion.type) {
                    case 'correction':
                        // Replace content for corrections
                        mergedContent = suggestion.content;
                        break;
                    case 'improvement':
                        // Replace content for improvements
                        mergedContent = suggestion.content;
                        break;
                    case 'expansion':
                        // Append content for expansions
                        mergedContent += '\n\n' + suggestion.content;
                        break;
                    case 'formatting':
                        // Apply formatting (simplified)
                        mergedContent = this.applyFormatting(mergedContent, suggestion.content);
                        break;
                }
            }
        }

        return mergedContent;
    }

    /**
     * Applies formatting suggestions to content
     */
    private static applyFormatting(content: string, formattingSuggestion: string): string {
        // This is a simplified implementation
        // In practice, you'd want more sophisticated formatting logic
        return formattingSuggestion || content;
    }

    /**
     * Generates a handoff message for AI to user transition
     */
    static generateHandoffMessage(
        draft: Draft,
        confidence: number,
        suggestions: AIDraftSuggestion[]
    ): string {
        const reasons: string[] = [];

        if (confidence < 0.6) {
            reasons.push('low confidence in the generated content');
        }

        const criticalCorrections = suggestions.filter(
            s => s.type === 'correction' && s.confidence > 0.8
        );
        if (criticalCorrections.length > 0) {
            reasons.push(`${criticalCorrections.length} critical correction(s) needed`);
        }

        if (this.isMissingCriticalMetadata(draft)) {
            reasons.push('missing critical metadata');
        }

        if (reasons.length === 0) {
            return 'AI draft ready for your review and finalization.';
        }

        return `AI draft requires your attention: ${reasons.join(', ')}. Please review and finalize.`;
    }

    /**
     * Calculates analytics for AI draft usage
     */
    static calculateAnalytics(drafts: Draft[]): AIDraftAnalytics {
        const aiDrafts = drafts.filter(d => d.isAIGenerated);

        if (aiDrafts.length === 0) {
            return {
                totalGenerated: 0,
                totalApproved: 0,
                totalRejected: 0,
                totalModified: 0,
                averageConfidence: 0,
                mostUsedType: 'email',
                suggestionsApplied: 0,
            };
        }

        const typeCounts = aiDrafts.reduce((acc, draft) => {
            acc[draft.type] = (acc[draft.type] || 0) + 1;
            return acc;
        }, {} as Record<DraftType, number>);

        const mostUsedType = Object.entries(typeCounts).reduce((a, b) =>
            typeCounts[a[0] as DraftType] > typeCounts[b[0] as DraftType] ? a : b
        )[0] as DraftType;

        const approvedCount = aiDrafts.filter(d =>
            d.metadata.ai_status === 'approved'
        ).length;

        const rejectedCount = aiDrafts.filter(d =>
            d.metadata.ai_status === 'rejected'
        ).length;

        const modifiedCount = aiDrafts.filter(d =>
            d.metadata.ai_improved === true
        ).length;

        const totalSuggestionsApplied = aiDrafts.reduce((sum, draft) => {
            const appliedSuggestions = draft.metadata.applied_suggestions as string[] || [];
            return sum + appliedSuggestions.length;
        }, 0);

        // Calculate average confidence (simplified)
        const averageConfidence = aiDrafts.reduce((sum, draft) => {
            const confidence = draft.metadata.ai_confidence as number || 0.7;
            return sum + confidence;
        }, 0) / aiDrafts.length;

        return {
            totalGenerated: aiDrafts.length,
            totalApproved: approvedCount,
            totalRejected: rejectedCount,
            totalModified: modifiedCount,
            averageConfidence,
            mostUsedType,
            suggestionsApplied: totalSuggestionsApplied,
        };
    }

    /**
     * Validates AI draft content quality
     */
    static validateAIDraftQuality(draft: Draft): {
        isValid: boolean;
        issues: string[];
        score: number;
    } {
        const issues: string[] = [];
        let score = 100;

        // Check content length
        if (draft.content.length < 20) {
            issues.push('Content is too short');
            score -= 30;
        }

        // Check for missing metadata
        if (this.isMissingCriticalMetadata(draft)) {
            issues.push('Missing critical metadata');
            score -= 25;
        }

        // Check for common AI artifacts
        if (draft.content.includes('I am an AI') || draft.content.includes('As an AI')) {
            issues.push('Contains AI self-reference');
            score -= 15;
        }

        // Check for repetitive content
        const words = draft.content.toLowerCase().split(/\s+/);
        const uniqueWords = new Set(words);
        const repetitionRatio = uniqueWords.size / words.length;
        if (repetitionRatio < 0.6) {
            issues.push('Content may be repetitive');
            score -= 10;
        }

        // Check for proper formatting
        if (!draft.content.includes('\n') && draft.content.length > 200) {
            issues.push('Content lacks proper formatting');
            score -= 5;
        }

        return {
            isValid: score >= 70,
            issues,
            score: Math.max(0, score),
        };
    }

    /**
     * Extracts key insights from AI draft for user review
     */
    static extractDraftInsights(draft: Draft): {
        keyPoints: string[];
        tone: string;
        length: 'short' | 'medium' | 'long';
        complexity: 'simple' | 'moderate' | 'complex';
    } {
        const content = draft.content.toLowerCase();
        const wordCount = draft.content.split(/\s+/).length;

        // Determine tone
        let tone = 'neutral';
        if (content.includes('please') || content.includes('kindly')) {
            tone = 'polite';
        } else if (content.includes('urgent') || content.includes('asap')) {
            tone = 'urgent';
        } else if (content.includes('thank you') || content.includes('appreciate')) {
            tone = 'grateful';
        }

        // Determine length
        let length: 'short' | 'medium' | 'long' = 'medium';
        if (wordCount < 50) length = 'short';
        else if (wordCount > 200) length = 'long';

        // Determine complexity
        let complexity: 'simple' | 'moderate' | 'complex' = 'moderate';
        const avgWordLength = draft.content.replace(/[^\w\s]/g, '').split(/\s+/).reduce((sum, word) => sum + word.length, 0) / wordCount;
        if (avgWordLength < 4.5) complexity = 'simple';
        else if (avgWordLength > 6) complexity = 'complex';

        // Extract key points (simplified)
        const sentences = draft.content.split(/[.!?]+/).filter(s => s.trim().length > 10);
        const keyPoints = sentences.slice(0, 3).map(s => s.trim());

        return {
            keyPoints,
            tone,
            length,
            complexity,
        };
    }
} 