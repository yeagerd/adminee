"use client";

import { useMemo, useState } from 'react';
import { Draft, DraftMetadata } from '@/types/draft';
import { DraftEditor } from '@/components/draft/draft-editor';
import { DraftActions } from '@/components/draft/draft-actions';
import { DraftMetadata as DraftMetadataComponent } from '@/components/draft/draft-metadata';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { ChevronDown, ChevronUp, Reply, ReplyAll, Forward } from 'lucide-react';

interface EmailThreadDraftProps {
  initialDraft: Draft;
  onClose?: () => void;
}

const MODE_LABEL: Record<'reply' | 'reply_all' | 'forward', string> = {
  reply: 'Reply',
  reply_all: 'Reply All',
  forward: 'Forward',
};

export default function EmailThreadDraft({ initialDraft, onClose }: EmailThreadDraftProps) {
  const [draft, setDraft] = useState<Draft>(initialDraft);
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<'reply' | 'reply_all' | 'forward'>(() => {
    const subj = (initialDraft.metadata.subject || '').toLowerCase();
    if (subj.startsWith('fwd:') || subj.startsWith('fwd') || subj.startsWith('fwd')) return 'forward';
    if ((initialDraft.metadata.recipients?.length || 0) > 1 || (initialDraft.metadata.cc?.length || 0) > 0) return 'reply_all';
    return 'reply';
  });

  const handleContentChange = (content: string) => {
    setDraft((prev) => ({ ...prev, content, updatedAt: new Date().toISOString() }));
  };

  const handleMetadataChange = (metadata: Partial<DraftMetadata>) => {
    setDraft((prev) => ({
      ...prev,
      metadata: { ...prev.metadata, ...metadata },
      updatedAt: new Date().toISOString(),
    }));
  };

  const summary = useMemo(() => {
    const count = draft.metadata.recipients?.length || 0;
    const label = mode === 'reply_all' ? `Reply-All to ${count} ${count === 1 ? 'person' : 'people'}` : MODE_LABEL[mode];
    const subject = draft.metadata.subject ? ` • ${draft.metadata.subject}` : '';
    return `${label}${subject}`;
  }, [draft.metadata.recipients, draft.metadata.subject, mode]);

  const handleActionComplete = (action: string, success: boolean) => {
    if (success && (action === 'send' || action === 'discard')) {
      onClose?.();
    }
  };

  const changeMode = (next: 'reply' | 'reply_all' | 'forward') => {
    setMode(next);
    // Adjust recipients when switching modes
    const to = draft.metadata.recipients || [];
    const cc = draft.metadata.cc || [];
    if (next === 'reply') {
      // keep only the first recipient
      handleMetadataChange({ recipients: to.slice(0, 1), cc: [] });
    } else if (next === 'reply_all') {
      // leave as-is (user can edit)
      handleMetadataChange({ recipients: to, cc });
    } else if (next === 'forward') {
      // clear recipients
      handleMetadataChange({ recipients: [], cc: [], bcc: [] });
    }
  };

  return (
    <div className="mt-3 border rounded-md bg-muted/20">
      <Collapsible open={open} onOpenChange={setOpen}>
        {/* Header row always on top */}
        <div className="p-3 border-b bg-muted/30 flex items-center justify-between gap-2">
          <div className="text-sm text-muted-foreground truncate">{summary}</div>
          <div className="flex items-center gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="flex items-center gap-1">
                  {MODE_LABEL[mode]}
                  <ChevronDown className="h-3 w-3 opacity-70" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => changeMode('reply')}>
                  <Reply className="h-4 w-4 mr-2" /> Reply
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => changeMode('reply_all')}>
                  <ReplyAll className="h-4 w-4 mr-2" /> Reply All
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => changeMode('forward')}>
                  <Forward className="h-4 w-4 mr-2" /> Forward
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm" aria-label="Toggle details">
                {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </CollapsibleTrigger>
          </div>
        </div>
        <CollapsibleContent>
          <div className="p-3 border-b bg-background">
            <DraftMetadataComponent draft={draft} onUpdate={handleMetadataChange} type={draft.type} />
          </div>
        </CollapsibleContent>
      </Collapsible>

      <div className="p-3">
        <DraftEditor
          type={draft.type}
          content={draft.content}
          onUpdate={handleContentChange}
          updatedAt={draft.updatedAt}
        />
      </div>
      <div className="p-3 border-t bg-muted/30">
        <DraftActions draft={draft} onActionComplete={handleActionComplete} />
      </div>
    </div>
  );
}