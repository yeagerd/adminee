'use client';

import { useSettings } from "@/contexts/settings-context";
import { BillingContent } from "./settings/billing-content";
import { IntegrationsContent } from "./settings/integrations-content";
import { NotificationsContent } from "./settings/notifications-content";
import { ProfileContent } from "./settings/profile-content";
import { SecurityContent } from "./settings/security-content";

export function SettingsContent() {
    const { currentPage } = useSettings();

    switch (currentPage) {
        case 'profile':
            return <ProfileContent />;
        case 'integrations':
            return <IntegrationsContent />;
        case 'billing':
            return <BillingContent />;
        case 'security':
            return <SecurityContent />;
        case 'notifications':
            return <NotificationsContent />;
        default:
            return <ProfileContent />;
    }
} 