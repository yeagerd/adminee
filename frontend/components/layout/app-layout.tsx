import Navbar from "@/components/navbar";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { SidebarProvider } from "@/components/ui/sidebar";
import { useChatPanelState } from "@/contexts/chat-panel-context";
import React, { ReactElement, ReactNode, RefObject, useRef } from "react";

interface AppLayoutProps {
    sidebar?: ReactNode;
    main: ReactNode;
    draft?: ReactElement<{ containerRef?: RefObject<HTMLDivElement> }>;
    draftPane?: ReactNode;
    hasActiveDraft?: boolean;
}

export function AppLayout({ sidebar, main, draft, draftPane, hasActiveDraft = false }: AppLayoutProps) {
    const chatPaneRef = useRef<HTMLDivElement>(null) as React.RefObject<HTMLDivElement>;
    const { isOpen, width, setWidth } = useChatPanelState();

    // Calculate panel sizes based on chat state
    const getPanelSizes = () => {
        if (!isOpen) {
            return { mainSize: 100, chatSize: 0 };
        }

        // Calculate chat panel size as percentage of total width
        // Assuming a reasonable total width for calculation
        const totalWidth = 1200; // Approximate total width
        const chatSizePercent = Math.round((width / totalWidth) * 100);
        const mainSizePercent = 100 - chatSizePercent;

        return { mainSize: mainSizePercent, chatSize: chatSizePercent };
    };

    const { mainSize, chatSize } = getPanelSizes();

    const handlePanelResize = (sizes: number[]) => {
        if (sizes.length >= 2) {
            // Calculate actual width from percentage
            const totalWidth = 1200; // Approximate total width
            const newChatWidth = Math.round((sizes[1] / 100) * totalWidth);
            setWidth(newChatWidth);
        }
    };

    return (
        <div className="flex flex-col h-screen w-full bg-background">
            <Navbar />
            <div className="flex flex-1 min-h-0 w-full">
                <div className="h-full flex items-stretch shrink-0 max-w-xs">
                    <SidebarProvider>
                        {sidebar || <div className="h-full w-full border-r bg-sidebar flex items-center justify-center text-muted-foreground">Sidebar</div>}
                    </SidebarProvider>
                </div>
                <div className="flex-1 min-w-0 h-full flex flex-col">
                    {draft ? (
                        <ResizablePanelGroup
                            key={`chat-${isOpen ? 'open' : 'closed'}-${chatSize}`}
                            className="flex-1 flex min-w-0"
                            direction="horizontal"
                            onLayout={handlePanelResize}
                        >
                            <ResizablePanel minSize={30} defaultSize={mainSize} className="h-full">
                                {draftPane && hasActiveDraft ? (
                                    <ResizablePanelGroup direction="vertical" className="h-full">
                                        <ResizablePanel minSize={10} defaultSize={50} className="h-full">
                                            <div className="h-full overflow-auto">
                                                {main || <div className="flex-1 flex items-center justify-center text-muted-foreground">Main Pane</div>}
                                            </div>
                                        </ResizablePanel>
                                        <ResizableHandle withHandle />
                                        <ResizablePanel minSize={10} defaultSize={50} className="h-full min-h-0 border-t bg-card">
                                            <div className="h-full overflow-auto">
                                                {draftPane}
                                            </div>
                                        </ResizablePanel>
                                    </ResizablePanelGroup>
                                ) : (
                                    <div className="h-full flex flex-col">
                                        <div className="flex-1 overflow-auto">
                                            {main || <div className="flex-1 flex items-center justify-center text-muted-foreground">Main Pane</div>}
                                        </div>
                                        {draftPane && !hasActiveDraft && (
                                            <div className="border-t bg-card overflow-auto">
                                                {draftPane}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </ResizablePanel>
                            {isOpen && (
                                <>
                                    <ResizableHandle withHandle />
                                    <ResizablePanel
                                        minSize={20}
                                        defaultSize={chatSize}
                                        collapsible
                                        className="h-full border-l bg-card"
                                    >
                                        <div className="h-full overflow-auto" ref={chatPaneRef}>
                                            {draft
                                                ? React.cloneElement(draft, { containerRef: chatPaneRef })
                                                : <div className="flex-1 flex items-center justify-center text-muted-foreground">Chat Pane</div>}
                                        </div>
                                    </ResizablePanel>
                                </>
                            )}
                        </ResizablePanelGroup>
                    ) : (
                        <div className="flex-1 min-w-0 h-full flex flex-col">
                            {draftPane && hasActiveDraft ? (
                                <ResizablePanelGroup direction="vertical" className="h-full">
                                    <ResizablePanel minSize={10} defaultSize={50} className="h-full">
                                        <div className="h-full overflow-auto">
                                            {main || <div className="flex-1 flex items-center justify-center text-muted-foreground">Main Pane</div>}
                                        </div>
                                    </ResizablePanel>
                                    <ResizableHandle withHandle />
                                    <ResizablePanel minSize={10} defaultSize={50} className="h-full min-h-0 border-t bg-card">
                                        <div className="h-full overflow-auto">
                                            {draftPane}
                                        </div>
                                    </ResizablePanel>
                                </ResizablePanelGroup>
                            ) : (
                                <>
                                    <div className="flex-1 overflow-auto">
                                        {main || <div className="flex-1 flex items-center justify-center text-muted-foreground">Main Pane</div>}
                                    </div>
                                    {draftPane && !hasActiveDraft && (
                                        <div className="border-t bg-card overflow-auto">
                                            {draftPane}
                                        </div>
                                    )}
                                </>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default AppLayout;