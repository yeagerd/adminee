"use client";

import { useState } from 'react';
import { Draft, DraftMetadata } from '@/types/draft';
import { DraftEditor } from '@/components/draft/draft-editor';
import { DraftActions } from '@/components/draft/draft-actions';
import { DraftMetadata as DraftMetadataComponent } from '@/components/draft/draft-metadata';

interface EmailThreadDraftProps {
  initialDraft: Draft;
  onClose?: () => void;
}

export default function EmailThreadDraft({ initialDraft, onClose }: EmailThreadDraftProps) {
  const [draft, setDraft] = useState<Draft>(initialDraft);

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

  const handleActionComplete = (action: string, success: boolean) => {
    if (success && (action === 'send' || action === 'discard')) {
      onClose?.();
    }
  };

  return (
    <div className="mt-3 border rounded-md bg-muted/20">
      <div className="p-3 border-b bg-muted/30">
        <DraftActions draft={draft} onActionComplete={handleActionComplete} />
      </div>
      <div className="p-3 border-b">
        <DraftMetadataComponent draft={draft} onUpdate={handleMetadataChange} type={draft.type} />
      </div>
      <div className="p-3">
        <DraftEditor
          type={draft.type}
          content={draft.content}
          onUpdate={handleContentChange}
          updatedAt={draft.updatedAt}
        />
      </div>
    </div>
  );
}