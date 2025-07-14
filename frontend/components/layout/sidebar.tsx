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
import { BarChart3, BookOpen, Calendar, ClipboardList, FileText, Mail, MessageSquare, Package, TrendingUp } from "lucide-react";

export type Tool = "calendar" | "email" | "documents" | "tasks" | "chat" | "packages" | "research" | "pulse" | "insights";

const navigationItems = [
    { id: "calendar" as Tool, title: "Calendar", icon: Calendar },
    { id: "email" as Tool, title: "Email", icon: Mail },
    { id: "documents" as Tool, title: "Documents", icon: FileText },
    { id: "tasks" as Tool, title: "Tasks", icon: ClipboardList },
    { id: "chat" as Tool, title: "Chat", icon: MessageSquare },
    { id: "packages" as Tool, title: "Package Tracker", icon: Package },
    { id: "research" as Tool, title: "Research", icon: BookOpen },
    { id: "pulse" as Tool, title: "Pulse", icon: TrendingUp },
    { id: "insights" as Tool, title: "Insights", icon: BarChart3, badge: "Soon" },
];

interface SidebarProps {
    activeTool: Tool;
    onToolChange: (tool: Tool) => void;
}

export function Sidebar({ activeTool, onToolChange }: SidebarProps) {
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
                            {navigationItems.map((item) => (
                                <SidebarMenuItem key={item.id}>
                                    <SidebarMenuButton
                                        isActive={activeTool === item.id}
                                        onClick={() => onToolChange(item.id)}
                                        disabled={item.badge === "Soon"}
                                        tooltip={item.title}
                                    >
                                        <item.icon className="h-4 w-4" />
                                        <span>{item.title}</span>
                                        {item.badge && (
                                            <span className="ml-auto text-xs bg-muted px-1.5 py-0.5 rounded group-data-[collapsible=icon]:hidden">
                                                {item.badge}
                                            </span>
                                        )}
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            ))}
                        </SidebarMenu>
                    </SidebarGroupContent>
                </SidebarGroup>
            </SidebarContent>
        </UISidebar>
    );
}

export default Sidebar; 