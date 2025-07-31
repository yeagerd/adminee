import Navbar from "@/components/navbar";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { SidebarProvider } from "@/components/ui/sidebar";
import { useChatPanelState } from "@/contexts/chat-panel-context";
import React, { ReactElement, ReactNode, RefObject, useEffect, useRef, useState } from "react";

interface AppLayoutProps {
    sidebar?: ReactNode;
    main: ReactNode;
    draft?: ReactElement<{ containerRef?: RefObject<HTMLDivElement> }>;
    draftPane?: ReactNode;
    hasActiveDraft?: boolean;
}

export function AppLayout({ sidebar, main, draft, draftPane, hasActiveDraft = false }: AppLayoutProps) {
    const chatPaneRef = useRef<HTMLDivElement>(null) as React.RefObject<HTMLDivElement>;
    const containerRef = useRef<HTMLDivElement>(null);
    const { isOpen, width, setWidth } = useChatPanelState();
    const [containerWidth, setContainerWidth] = useState<number>(0);

    // Track container width for responsive sizing
    useEffect(() => {
        const updateContainerWidth = () => {
            if (containerRef.current) {
                setContainerWidth(containerRef.current.offsetWidth);
            }
        };

        updateContainerWidth();
        const resizeObserver = new ResizeObserver(updateContainerWidth);

        if (containerRef.current) {
            resizeObserver.observe(containerRef.current);
        }

        return () => resizeObserver.disconnect();
    }, []);

    // Calculate panel sizes based on chat state
    const getPanelSizes = () => {
        if (!isOpen) {
            return { mainSize: 100, chatSize: 0 };
        }

        // Use actual container width for accurate percentage calculations
        const totalWidth = containerWidth || 1200; // Fallback to 1200px if not measured yet

        // Ensure width doesn't exceed container width
        const clampedWidth = Math.min(width, totalWidth);
        const chatSizePercent = Math.max(0, Math.min(100, Math.round((clampedWidth / totalWidth) * 100)));
        const mainSizePercent = Math.max(0, 100 - chatSizePercent);

        return { mainSize: mainSizePercent, chatSize: chatSizePercent };
    };

    const { mainSize, chatSize } = getPanelSizes();

    const handlePanelResize = (sizes: number[]) => {
        if (sizes.length >= 2) {
            // Calculate actual width from percentage using real container width
            const totalWidth = containerWidth || 1200; // Fallback to 1200px if not measured yet
            const newChatWidth = Math.max(0, Math.round((sizes[1] / 100) * totalWidth));
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
                <div ref={containerRef} className="flex-1 min-w-0 h-full flex flex-col">
                    {draft ? (
                        <ResizablePanelGroup
                            className="flex-1 flex min-w-0"
                            direction="horizontal"
                            onLayout={handlePanelResize}
                        >
                            <ResizablePanel minSize={30} size={mainSize} className="h-full">
                                {draftPane && hasActiveDraft ? (
                                    <ResizablePanelGroup direction="vertical" className="h-full">
                                        <ResizablePanel minSize={10} size={50} className="h-full">
                                            <div className="h-full overflow-auto">
                                                {main || <div className="flex-1 flex items-center justify-center text-muted-foreground">Main Pane</div>}
                                            </div>
                                        </ResizablePanel>
                                        <ResizableHandle withHandle />
                                        <ResizablePanel minSize={10} size={50} className="h-full min-h-0 border-t bg-card">
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
                                        size={chatSize}
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
                        <div ref={containerRef} className="flex-1 min-w-0 h-full flex flex-col">
                            {draftPane && hasActiveDraft ? (
                                <ResizablePanelGroup direction="vertical" className="h-full">
                                    <ResizablePanel minSize={10} size={50} className="h-full">
                                        <div className="h-full overflow-auto">
                                            {main || <div className="flex-1 flex items-center justify-center text-muted-foreground">Main Pane</div>}
                                        </div>
                                    </ResizablePanel>
                                    <ResizableHandle withHandle />
                                    <ResizablePanel minSize={10} size={50} className="h-full min-h-0 border-t bg-card">
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