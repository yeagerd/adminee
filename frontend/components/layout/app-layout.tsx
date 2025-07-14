import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { SidebarProvider } from "@/components/ui/sidebar";
import { ReactNode } from "react";

interface AppLayoutProps {
    sidebar?: ReactNode;
    main: ReactNode;
    draft: ReactNode;
}

export function AppLayout({ sidebar, main, draft }: AppLayoutProps) {
    return (
        <SidebarProvider>
            <div className="flex h-screen w-full bg-background">
                {/* Sidebar (left) */}
                <div className="hidden md:flex h-full border-r bg-sidebar min-w-[64px] max-w-xs w-56">
                    {sidebar || <div className="flex-1 flex items-center justify-center text-muted-foreground">Sidebar</div>}
                </div>
                {/* Main + Draft (resizable) */}
                <ResizablePanelGroup className="flex-1 flex" direction="horizontal">
                    {/* Main Pane */}
                    <ResizablePanel minSize={30} defaultSize={60} className="h-full">
                        <div className="h-full overflow-auto">
                            {main || <div className="flex-1 flex items-center justify-center text-muted-foreground">Main Pane</div>}
                        </div>
                    </ResizablePanel>
                    {/* Handle */}
                    <ResizableHandle withHandle />
                    {/* Draft Pane (right) */}
                    <ResizablePanel minSize={20} defaultSize={30} collapsible className="h-full border-l bg-card">
                        <div className="h-full overflow-auto">
                            {draft || <div className="flex-1 flex items-center justify-center text-muted-foreground">Draft Pane</div>}
                        </div>
                    </ResizablePanel>
                </ResizablePanelGroup>
            </div>
        </SidebarProvider>
    );
}

export default AppLayout; 