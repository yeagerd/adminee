import { DraftPane as DraftPaneComponent } from "@/components/draft/draft-pane";
import { ReactNode } from "react";

interface DraftPaneProps {
    children?: ReactNode;
    userId?: string;
}

export function DraftPane({ children, userId }: DraftPaneProps) {
    if (children) {
        return <div className="h-full overflow-auto">{children}</div>;
    }

    return <DraftPaneComponent userId={userId} />;
}

export default DraftPane; 