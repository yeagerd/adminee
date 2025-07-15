import {
    SidebarContent,
    SidebarGroup,
    SidebarGroupContent,
    SidebarHeader,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
    SidebarTrigger,
    Sidebar as UISidebar,
} from "@/components/ui/sidebar";
import { useToolStateUtils } from "@/hooks/use-tool-state";
import { getToolBadge, isToolAvailable } from "@/lib/tool-routing";
import { NavigationItem, Tool } from "@/types/navigation";
import { BarChart3, BookOpen, Calendar, ClipboardList, FileText, Mail, Package, TrendingUp } from "lucide-react";

const navigationItems: NavigationItem[] = [
    { id: "calendar", title: "Calendar", icon: Calendar, path: "/dashboard?tool=calendar", enabled: true },
    { id: "email", title: "Email", icon: Mail, path: "/dashboard?tool=email", enabled: true },
    { id: "documents", title: "Documents", icon: FileText, path: "/dashboard?tool=documents", enabled: true },
    { id: "tasks", title: "Tasks", icon: ClipboardList, path: "/dashboard?tool=tasks", enabled: true },
    { id: "packages", title: "Package Tracker", icon: Package, path: "/dashboard?tool=packages", enabled: true },
    { id: "research", title: "Research", icon: BookOpen, path: "/dashboard?tool=research", enabled: true },
    { id: "pulse", title: "Pulse", icon: TrendingUp, path: "/dashboard?tool=pulse", enabled: true },
    { id: "insights", title: "Insights", icon: BarChart3, path: "/dashboard?tool=insights", enabled: false },
];

interface SidebarProps {
    activeTool?: Tool;
    onToolChange?: (tool: Tool) => void;
}

export function Sidebar({ onToolChange }: SidebarProps) {
    const { setActiveTool, isToolEnabled, isActiveTool } = useToolStateUtils();

    // Use context state if no props provided
    const handleToolChange = onToolChange || setActiveTool;

    return (
        <UISidebar collapsible="icon" className="border-r">
            <SidebarHeader className="border-b p-2">
                <div className="flex items-center space-x-2">
                    <SidebarTrigger />
                    <span className="font-semibold group-data-[collapsible=icon]:hidden">Briefly</span>
                </div>
            </SidebarHeader>
            <SidebarContent>
                <SidebarGroup>
                    <SidebarGroupContent>
                        <SidebarMenu>
                            {navigationItems.map((item) => {
                                const isEnabled = isToolEnabled(item.id);
                                const badge = getToolBadge(item.id);
                                const isAvailable = isToolAvailable(item.id);

                                return (
                                    <SidebarMenuItem key={item.id}>
                                        <SidebarMenuButton
                                            isActive={isActiveTool(item.id)}
                                            onClick={() => handleToolChange(item.id)}
                                            disabled={!isEnabled || !isAvailable}
                                            tooltip={item.title}
                                        >
                                            <item.icon className="h-4 w-4" />
                                            <span>{item.title}</span>
                                            {badge && (
                                                <span className="ml-auto text-xs bg-muted px-1.5 py-0.5 rounded group-data-[collapsible=icon]:hidden">
                                                    {badge}
                                                </span>
                                            )}
                                        </SidebarMenuButton>
                                    </SidebarMenuItem>
                                );
                            })}
                        </SidebarMenu>
                    </SidebarGroupContent>
                </SidebarGroup>
            </SidebarContent>
        </UISidebar>
    );
}

export default Sidebar; 