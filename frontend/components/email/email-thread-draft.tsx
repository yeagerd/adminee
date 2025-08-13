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
import DOMPurify from 'dompurify';

interface EmailThreadDraftProps {
  initialDraft: Draft;
  onClose?: () => void;
  quotedHeader?: string;
  quotedBody?: string;
  quotedIsHtml?: boolean;
}

const MODE_LABEL: Record<'reply' | 'reply_all' | 'forward', string> = {
  reply: 'Reply',
  reply_all: 'Reply All',
  forward: 'Forward',
};

export default function EmailThreadDraft({ initialDraft, onClose, quotedHeader, quotedBody, quotedIsHtml = false }: EmailThreadDraftProps) {
  const [draft, setDraft] = useState<Draft>(initialDraft);
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<'reply' | 'reply_all' | 'forward'>(() => {
    const subj = (initialDraft.metadata.subject || '').toLowerCase();
    if (subj.startsWith('fwd:') || subj.startsWith('fwd') || subj.startsWith('fwd')) return 'forward';
    if ((initialDraft.metadata.recipients?.length || 0) > 1 || (initialDraft.metadata.cc?.length || 0) > 0) return 'reply_all';
    return 'reply';
  });
  const [showQuoted, setShowQuoted] = useState(false);

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
    const to = draft.metadata.recipients || [];
    const cc = draft.metadata.cc || [];
    if (next === 'reply') {
      handleMetadataChange({ recipients: to.slice(0, 1), cc: [] });
    } else if (next === 'reply_all') {
      handleMetadataChange({ recipients: to, cc });
    } else if (next === 'forward') {
      handleMetadataChange({ recipients: [], cc: [], bcc: [] });
    }
  };

  return (
    <div id={`thread-draft-${draft.id}`} className="mt-3 border rounded-md bg-white">
      <Collapsible open={open} onOpenChange={setOpen}>
        {/* Header row always on top */}
        <div className="p-3 border-b bg-white flex items-center justify-between gap-2">
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
          <div className="p-3 border-b bg-white">
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

      {(quotedHeader || quotedBody) && (
        <div className="px-3 pb-2">
          <button
            className="text-sm text-blue-600 hover:underline"
            onClick={() => setShowQuoted((s) => !s)}
            type="button"
          >
            {showQuoted ? 'Hide quoted text' : 'Show quoted text'}
          </button>
          {showQuoted && (
            <div className="mt-2 border rounded bg-gray-50 p-3">
              {quotedHeader && (
                <pre className="text-xs text-gray-700 whitespace-pre-wrap mb-2">{quotedHeader}</pre>
              )}
              {quotedBody && quotedIsHtml ? (
                <div
                  className="prose prose-sm max-w-none"
                  dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(quotedBody) }}
                />
              ) : (
                quotedBody && <pre className="text-xs text-gray-700 whitespace-pre-wrap">{quotedBody}</pre>
              )}
            </div>
          )}
        </div>
      )}

      <div className="p-3 border-t bg-white">
        <DraftActions draft={draft} onActionComplete={handleActionComplete} />
      </div>
    </div>
  );
}