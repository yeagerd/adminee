import { ReactNode } from "react";

interface DraftPaneProps {
    children: ReactNode;
}

export function DraftPane({ children }: DraftPaneProps) {
    return <div className="h-full overflow-auto">{children}</div>;
}

export default DraftPane; 