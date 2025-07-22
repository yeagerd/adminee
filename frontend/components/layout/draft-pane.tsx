import { DraftPane as DraftPaneComponent } from "@/components/draft/draft-pane";
import { Draft, DraftMetadata, DraftType } from "@/types/draft";
import { ReactNode } from "react";

interface DraftPaneProps {
    children?: ReactNode;
    draft: Draft | null;
    onUpdate: (updates: Partial<Draft>) => void;
    onMetadataChange: (metadata: Partial<DraftMetadata>) => void;
    onTypeChange: (type: DraftType) => void;
    userId?: string;
}

export function DraftPane({ children, draft, onUpdate, onMetadataChange, onTypeChange, userId }: DraftPaneProps) {
    if (children) {
        return <div className="h-full overflow-auto">{children}</div>;
    }

    return <DraftPaneComponent draft={draft} onUpdate={onUpdate} onMetadataChange={onMetadataChange} userId={userId} />;
}

export default DraftPane; 