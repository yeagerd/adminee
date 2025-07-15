import { Card } from '@/components/ui/card';
import { formatDraftDate } from '@/lib/draft-utils';
import { Draft } from '@/types/draft';

export function DraftCard({ draft, onClick }: { draft: Draft; onClick?: () => void }) {
    return (
        <Card className="mb-2 cursor-pointer hover:shadow" onClick={onClick}>
            <div className="flex items-center justify-between">
                <span className="text-xs uppercase text-muted-foreground">{draft.type}</span>
                <span className="text-xs text-muted-foreground">{formatDraftDate(draft.updatedAt)}</span>
            </div>
            <div className="font-medium truncate">
                {draft.metadata?.subject || draft.metadata?.title || '(No subject)'}
            </div>
            <div className="text-sm text-muted-foreground truncate">
                {draft.content?.slice(0, 80) || '(No content)'}
            </div>
            <div className="mt-1 text-xs text-right">
                <span className="rounded bg-muted px-2 py-0.5">{draft.status}</span>
            </div>
        </Card>
    );
} 