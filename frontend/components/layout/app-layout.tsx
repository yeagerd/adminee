import Navbar from "@/components/navbar";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { SidebarProvider } from "@/components/ui/sidebar";
import { ReactNode } from "react";

interface AppLayoutProps {
    sidebar?: ReactNode;
    main: ReactNode;
    draft?: ReactNode;
}

export function AppLayout({ sidebar, main, draft }: AppLayoutProps) {
    return (
        <div className="flex flex-col h-screen w-full bg-background">
            <Navbar />
            <div className="flex flex-1 min-h-0 w-full">
                <div className="h-full flex items-start">
                    <SidebarProvider>
                        {sidebar || <div className="w-56 min-w-[64px] max-w-xs h-full border-r bg-sidebar flex items-center justify-center text-muted-foreground">Sidebar</div>}
                    </SidebarProvider>
                </div>
                <div className="flex-1 min-w-0 h-full flex flex-col">
                    {draft ? (
                        <ResizablePanelGroup className="flex-1 flex min-w-0" direction="horizontal">
                            <ResizablePanel minSize={30} defaultSize={60} className="h-full">
                                <div className="h-full overflow-auto">
                                    {main || <div className="flex-1 flex items-center justify-center text-muted-foreground">Main Pane</div>}
                                </div>
                            </ResizablePanel>
                            <ResizableHandle withHandle />
                            <ResizablePanel minSize={20} defaultSize={30} collapsible className="h-full border-l bg-card">
                                <div className="h-full overflow-auto">
                                    {draft || <div className="flex-1 flex items-center justify-center text-muted-foreground">Draft Pane</div>}
                                </div>
                            </ResizablePanel>
                        </ResizablePanelGroup>
                    ) : (
                        <div className="flex-1 min-w-0 h-full">
                            <div className="h-full overflow-auto">
                                {main || <div className="flex-1 flex items-center justify-center text-muted-foreground">Main Pane</div>}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default AppLayout;