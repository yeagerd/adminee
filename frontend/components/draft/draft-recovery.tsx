import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { deleteDraft, formatDraftDate, listDrafts } from '@/lib/draft-utils';
import { Draft } from '@/types/draft';
import { AlertTriangle, RotateCcw } from 'lucide-react';
import { useEffect, useState } from 'react';

interface DraftRecoveryProps {
    onRecoverDraft: (draft: Draft) => void;
    onDismiss: () => void;
}

export function DraftRecovery({ onRecoverDraft, onDismiss }: DraftRecoveryProps) {
    const [recoveryDrafts, setRecoveryDrafts] = useState<Draft[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadRecoveryDrafts();
    }, []);

    const loadRecoveryDrafts = async () => {
        try {
            setIsLoading(true);
            setError(null);

            // Get drafts from the last 24 hours that might need recovery
            const result = await listDrafts({
                status: 'draft',
            });

            // Filter for drafts that might be recovery candidates (recent, unsaved changes)
            const recentDrafts = result.drafts.filter(draft => {
                const updatedAt = new Date(draft.updatedAt);
                const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
                return updatedAt > oneDayAgo;
            });

            setRecoveryDrafts(recentDrafts.slice(0, 5)); // Show max 5 recovery drafts
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load recovery drafts');
        } finally {
            setIsLoading(false);
        }
    };

    const handleRecoverDraft = (draft: Draft) => {
        onRecoverDraft(draft);
        onDismiss();
    };

    const handleDeleteDraft = async (draftId: string) => {
        try {
            await deleteDraft(draftId);
            setRecoveryDrafts(prev => prev.filter(d => d.id !== draftId));
        } catch (err) {
            console.error('Failed to delete recovery draft:', err);
        }
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center p-8">
                <div className="text-muted-foreground">Loading recovery drafts...</div>
            </div>
        );
    }

    if (error) {
        return (
            <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
            </Alert>
        );
    }

    if (recoveryDrafts.length === 0) {
        return (
            <div className="text-center text-muted-foreground py-8">
                <RotateCcw className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No recovery drafts found.</p>
                <Button variant="outline" size="sm" onClick={onDismiss} className="mt-2">
                    Dismiss
                </Button>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <RotateCcw className="h-5 w-5" />
                    <h3 className="text-lg font-semibold">Recovery Drafts</h3>
                </div>
                <Button variant="ghost" size="sm" onClick={onDismiss}>
                    Dismiss
                </Button>
            </div>

            <div className="space-y-3">
                {recoveryDrafts.map((draft) => (
                    <Card key={draft.id} className="border-orange-200 bg-orange-50">
                        <CardHeader className="pb-3">
                            <div className="flex items-center justify-between">
                                <CardTitle className="text-sm">
                                    {draft.metadata?.subject || draft.metadata?.title || `Draft ${draft.type}`}
                                </CardTitle>
                                <span className="text-xs text-muted-foreground">
                                    {formatDraftDate(draft.updatedAt)}
                                </span>
                            </div>
                            <CardDescription className="text-xs">
                                {draft.type} draft • {draft.content.slice(0, 100)}...
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="pt-0">
                            <div className="flex gap-2">
                                <Button
                                    size="sm"
                                    onClick={() => handleRecoverDraft(draft)}
                                    className="flex-1"
                                >
                                    Recover
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => handleDeleteDraft(draft.id)}
                                >
                                    Delete
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            <div className="text-xs text-muted-foreground text-center">
                These drafts were auto-saved and may contain unsaved changes.
            </div>
        </div>
    );
} 