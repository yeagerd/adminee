import { ChatPanelProvider } from '@/contexts/chat-panel-context';
import { IntegrationsProvider } from '@/contexts/integrations-context';
import { OfficeDataProvider } from '@/contexts/office-data-context';
import { UserPreferencesProvider } from '@/contexts/settings-context';

export default function AuthenticatedLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <OfficeDataProvider>
            <IntegrationsProvider>
                <UserPreferencesProvider>
                    <ChatPanelProvider>
                        {children}
                    </ChatPanelProvider>
                </UserPreferencesProvider>
            </IntegrationsProvider>
        </OfficeDataProvider>
    );
}
