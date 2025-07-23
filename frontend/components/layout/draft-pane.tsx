import { DraftPane as DraftPaneComponent } from "@/components/draft/draft-pane";
import { Draft, DraftMetadata, DraftType } from "@/types/draft";
import { ReactNode } from "react";

interface DraftPaneProps {
    children?: ReactNode;
    draft: Draft | null;
    onUpdate: (updates: Partial<Draft>) => void;
    onMetadataChange: (metadata: Partial<DraftMetadata>) => void;
    onTypeChange: (type: DraftType) => void;
}

export function DraftPane({ children, draft, onUpdate, onMetadataChange, onTypeChange }: DraftPaneProps) {
    if (children) {
        return <div className="h-full overflow-auto">{children}</div>;
    }

    return <DraftPaneComponent draft={draft} onUpdate={onUpdate} onMetadataChange={onMetadataChange} onTypeChange={onTypeChange} />;
}

export default DraftPane; 