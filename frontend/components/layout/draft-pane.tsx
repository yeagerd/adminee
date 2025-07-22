import { DraftPane as DraftPaneComponent } from "@/components/draft/draft-pane";
import { Draft } from "@/types/draft";
import { ReactNode } from "react";

interface DraftPaneProps {
    children?: ReactNode;
    draft: Draft | null;
}

export function DraftPane({ children, draft }: DraftPaneProps) {
    if (children) {
        return <div className="h-full overflow-auto">{children}</div>;
    }

    return <DraftPaneComponent draft={draft} />;
}

export default DraftPane; 