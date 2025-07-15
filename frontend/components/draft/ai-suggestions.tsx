import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { cn } from '@/lib/utils';
import { AIDraftSuggestion } from '@/services/ai-draft-service';
import {
    AlertCircle,
    CheckCircle,
    ChevronRight,
    Edit,
    Lightbulb,
    Plus,
    Sparkles,
    XCircle
} from 'lucide-react';

interface AISuggestionsProps {
    suggestions: AIDraftSuggestion[];
    onApplySuggestion?: (suggestion: AIDraftSuggestion) => void;
    onDismissSuggestion?: (suggestionId: string) => void;
    onGenerateMore?: () => void;
    className?: string;
}

export function AISuggestions({
    suggestions,
    onApplySuggestion,
    onDismissSuggestion,
    onGenerateMore,
    className,
}: AISuggestionsProps) {
    if (suggestions.length === 0) {
        return null;
    }

    const getSuggestionIcon = (type: AIDraftSuggestion['type']) => {
        switch (type) {
            case 'improvement':
                return <Lightbulb className="h-4 w-4 text-blue-500" />;
            case 'correction':
                return <AlertCircle className="h-4 w-4 text-red-500" />;
            case 'expansion':
                return <Plus className="h-4 w-4 text-green-500" />;
            case 'formatting':
                return <Edit className="h-4 w-4 text-purple-500" />;
            default:
                return <Sparkles className="h-4 w-4 text-gray-500" />;
        }
    };

    const getSuggestionBadgeVariant = (type: AIDraftSuggestion['type']) => {
        switch (type) {
            case 'improvement':
                return 'default' as const;
            case 'correction':
                return 'destructive' as const;
            case 'expansion':
                return 'secondary' as const;
            case 'formatting':
                return 'outline' as const;
            default:
                return 'secondary' as const;
        }
    };

    const getConfidenceColor = (confidence: number) => {
        if (confidence >= 0.8) return 'text-green-600';
        if (confidence >= 0.6) return 'text-yellow-600';
        return 'text-red-600';
    };

    return (
        <div className={cn('space-y-3', className)}>
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-purple-500" />
                    <h3 className="text-sm font-medium text-gray-900">AI Suggestions</h3>
                    <Badge variant="outline" className="text-xs">
                        {suggestions.length} suggestion{suggestions.length !== 1 ? 's' : ''}
                    </Badge>
                </div>
                {onGenerateMore && (
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={onGenerateMore}
                        className="text-xs"
                    >
                        <Sparkles className="h-3 w-3 mr-1" />
                        Generate More
                    </Button>
                )}
            </div>

            <div className="space-y-2">
                {suggestions.map((suggestion) => (
                    <Card key={suggestion.id} className="border-l-4 border-l-purple-200">
                        <Collapsible>
                            <CollapsibleTrigger asChild>
                                <CardHeader className="pb-2 cursor-pointer hover:bg-gray-50 transition-colors">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            {getSuggestionIcon(suggestion.type)}
                                            <CardTitle className="text-sm font-medium">
                                                {suggestion.title}
                                            </CardTitle>
                                            <Badge variant={getSuggestionBadgeVariant(suggestion.type)} className="text-xs">
                                                {suggestion.type}
                                            </Badge>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className={cn('text-xs', getConfidenceColor(suggestion.confidence))}>
                                                {Math.round(suggestion.confidence * 100)}% confidence
                                            </span>
                                            {/* The expandedSuggestions state was removed, so this will always be ChevronRight */}
                                            <ChevronRight className="h-4 w-4" />
                                        </div>
                                    </div>
                                </CardHeader>
                            </CollapsibleTrigger>

                            <CollapsibleContent>
                                <CardContent className="pt-0">
                                    <p className="text-sm text-gray-600 mb-3">
                                        {suggestion.description}
                                    </p>

                                    {suggestion.content && (
                                        <div className="bg-gray-50 p-3 rounded-md mb-3">
                                            <p className="text-sm font-medium text-gray-700 mb-1">Suggested content:</p>
                                            <p className="text-sm text-gray-600">{suggestion.content}</p>
                                        </div>
                                    )}

                                    <div className="flex items-center gap-2">
                                        {onApplySuggestion && (
                                            <Button
                                                size="sm"
                                                onClick={() => onApplySuggestion(suggestion)}
                                                className="flex items-center gap-1"
                                            >
                                                <CheckCircle className="h-3 w-3" />
                                                Apply
                                            </Button>
                                        )}
                                        {onDismissSuggestion && (
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => onDismissSuggestion(suggestion.id)}
                                                className="flex items-center gap-1"
                                            >
                                                <XCircle className="h-3 w-3" />
                                                Dismiss
                                            </Button>
                                        )}
                                    </div>
                                </CardContent>
                            </CollapsibleContent>
                        </Collapsible>
                    </Card>
                ))}
            </div>
        </div>
    );
} 