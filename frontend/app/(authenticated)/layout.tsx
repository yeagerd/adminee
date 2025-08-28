import { ChatPanelProvider } from '@/contexts/chat-panel-context';
import { IntegrationsProvider } from '@/contexts/integrations-context';
import { OfficeDataProvider } from '@/contexts/office-data-context';
import { UserPreferencesProvider } from '@/contexts/settings-context';
import { ContactsProvider } from '@/contexts/contacts-context';

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
                        <ContactsProvider>
                            {children}
                        </ContactsProvider>
                    </ChatPanelProvider>
                </UserPreferencesProvider>
            </IntegrationsProvider>
        </OfficeDataProvider>
    );
}
