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
import { BarChart3, BookOpen, Calendar, CalendarRange, Copy, FileText, ListChecks, Mail, Package, TrendingUp } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

const navigationItems: NavigationItem[] = [
    { id: "calendar", title: "Calendar", icon: Calendar, path: "/dashboard?tool=calendar", enabled: true },
    { id: "email", title: "Email", icon: Mail, path: "/dashboard?tool=email", enabled: true },
    { id: "documents", title: "Documents", icon: FileText, path: "/dashboard?tool=documents", enabled: false },
    { id: "tasks", title: "Tasks", icon: ListChecks, path: "/dashboard?tool=tasks", enabled: false },
    { id: "drafts", title: "Drafts", icon: Copy, path: "/dashboard?tool=drafts", enabled: true },
    { id: "meetings", title: "Meeting Polls", icon: CalendarRange, path: "/dashboard?tool=meetings", enabled: true },
    { id: "packages", title: "Package Tracker", icon: Package, path: "/dashboard?tool=packages", enabled: true },
    { id: "research", title: "Research", icon: BookOpen, path: "/dashboard?tool=research", enabled: false },
    { id: "pulse", title: "Pulse", icon: TrendingUp, path: "/dashboard?tool=pulse", enabled: false },
    { id: "insights", title: "Insights", icon: BarChart3, path: "/dashboard?tool=insights", enabled: false },
];

export function Sidebar() {
    const { isToolEnabled, isActiveTool } = useToolStateUtils();
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();

    const handleToolChange = (tool: Tool) => {
        const item = navigationItems.find(item => item.id === tool);
        if (!isToolEnabled(tool) || !isToolAvailable(tool) || !item?.enabled) return;
        const params = new URLSearchParams(searchParams.toString());
        params.set('tool', tool);
        router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    };

    return (
        <UISidebar collapsible="icon" className="border-r">
            <SidebarHeader className="border-b p-2">
                <div className="flex items-center space-x-2">
                    <SidebarTrigger />
                    <span className="font-semibold group-data-[collapsible=icon]:hidden">Tools</span>
                </div>
            </SidebarHeader>
            <SidebarContent>
                <SidebarGroup>
                    <SidebarGroupContent>
                        <SidebarMenu>
                            {navigationItems.map((item) => {
                                const isEnabled = isToolEnabled(item.id) && item.enabled;
                                const badge = getToolBadge(item.id);
                                const isAvailable = isToolAvailable(item.id);

                                return (
                                    <SidebarMenuItem key={item.id}>
                                        <SidebarMenuButton
                                            isActive={isActiveTool(item.id)}
                                            onClick={() => handleToolChange(item.id as Tool)}
                                            disabled={!isEnabled || !isAvailable}
                                            tooltip={item.title}
                                        >
                                            <item.icon className={isActiveTool(item.id) ? "h-4 w-4 text-teal-600" : "h-4 w-4"} />
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