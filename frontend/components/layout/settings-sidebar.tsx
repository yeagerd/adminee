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
import { SettingsPage, useSettings } from "@/contexts/settings-context";
import {
    ArrowLeft,
    Bell,
    CreditCard,
    Lock,
    Shield,
    User
} from "lucide-react";
import Link from "next/link";

interface SettingsNavigationItem {
    id: SettingsPage;
    title: string;
    icon: React.ComponentType<{ className?: string }>;
    path: string;
    enabled: boolean;
    badge?: string;
}

const settingsNavigationItems: SettingsNavigationItem[] = [
    {
        id: "profile",
        title: "Profile",
        icon: User,
        path: "/settings?page=profile",
        enabled: true
    },
    {
        id: "integrations",
        title: "Integrations",
        icon: Shield,
        path: "/settings?page=integrations",
        enabled: true
    },
    {
        id: "billing",
        title: "Billing",
        icon: CreditCard,
        path: "/settings?page=billing",
        enabled: false,
        badge: "Coming Soon"
    },
    {
        id: "security",
        title: "Security",
        icon: Lock,
        path: "/settings?page=security",
        enabled: false,
        badge: "Coming Soon"
    },
    {
        id: "notifications",
        title: "Notifications",
        icon: Bell,
        path: "/settings?page=notifications",
        enabled: false,
        badge: "Coming Soon"
    },
];

export function SettingsSidebar() {
    const { isPageEnabled, isActivePage, setCurrentPage } = useSettings();

    const handlePageChange = (page: SettingsPage) => {
        if (!isPageEnabled(page)) return;
        setCurrentPage(page);
    };

    return (
        <UISidebar collapsible="icon" className="border-r">
            <SidebarHeader className="border-b p-2">
                <div className="flex items-center space-x-2">
                    <SidebarTrigger />
                    <span className="font-semibold group-data-[collapsible=icon]:hidden">Settings</span>
                </div>
            </SidebarHeader>
            <SidebarContent>
                <SidebarGroup>
                    <SidebarGroupContent>
                        <SidebarMenu>
                            {/* Back to Dashboard */}
                            <SidebarMenuItem>
                                <SidebarMenuButton asChild>
                                    <Link href="/dashboard">
                                        <ArrowLeft className="h-4 w-4" />
                                        <span>Back to Dashboard</span>
                                    </Link>
                                </SidebarMenuButton>
                            </SidebarMenuItem>

                            {/* Settings Navigation Items */}
                            {settingsNavigationItems.map((item) => {
                                const isEnabled = isPageEnabled(item.id);
                                const isActive = isActivePage(item.id);

                                return (
                                    <SidebarMenuItem key={item.id}>
                                        <SidebarMenuButton
                                            isActive={isActive}
                                            onClick={() => handlePageChange(item.id)}
                                            disabled={!isEnabled}
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
                                );
                            })}
                        </SidebarMenu>
                    </SidebarGroupContent>
                </SidebarGroup>
            </SidebarContent>
        </UISidebar>
    );
}

export default SettingsSidebar; 