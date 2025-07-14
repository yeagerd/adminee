import { ReactNode } from "react";

interface MainPaneProps {
    children: ReactNode;
}

export function MainPane({ children }: MainPaneProps) {
    return <div className="h-full overflow-auto">{children}</div>;
}

export default MainPane; 