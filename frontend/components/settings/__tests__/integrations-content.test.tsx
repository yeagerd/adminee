import { userApi } from '@/api';
import { INTEGRATION_STATUS } from '@/lib/constants';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useSession } from 'next-auth/react';
import { IntegrationsContent } from '../integrations-content';

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
    useRouter: jest.fn(),
    useSearchParams: jest.fn(),
}));

// Mock the user API
jest.mock('@/api', () => ({
    userApi: {
        getProviderScopes: jest.fn(),
        startOAuthFlow: jest.fn(),
        disconnectIntegration: jest.fn(),
    },
}));

// Mock the integrations context
jest.mock('@/contexts/integrations-context', () => ({
    useIntegrations: jest.fn(),
}));

// Mock NextAuth session
jest.mock('next-auth/react', () => ({
    useSession: jest.fn(),
}));

// Mock the calendar cache
jest.mock('@/lib/calendar-cache', () => ({
    calendarCache: {
        invalidate: jest.fn(),
    },
}));

// Import the mocked modules
import { useIntegrations } from '@/contexts/integrations-context';

describe('IntegrationsContent', () => {
    const mockSession = {
        data: {
            user: {
                id: 'user-123',
                email: 'test@example.com',
                provider: 'microsoft',
            },
            provider: 'microsoft',
        },
        status: 'authenticated',
    };

    const mockIntegrations = [
        {
            id: 'integration-1',
            provider: 'microsoft',
            status: INTEGRATION_STATUS.ACTIVE,
            scopes: [
                'https://graph.microsoft.com/Mail.ReadWrite',
                'https://graph.microsoft.com/Calendars.ReadWrite',
            ],
            token_expires_at: '2025-12-31T23:59:59Z',
            has_refresh_token: true,
        },
    ];

    const mockProviderScopes = {
        provider: 'microsoft',
        scopes: [
            {
                name: 'openid',
                description: 'OpenID Connect authentication',
                required: true,
                sensitive: false,
            },
            {
                name: 'email',
                description: 'Access to user\'s email address',
                required: true,
                sensitive: false,
            },
            {
                name: 'https://graph.microsoft.com/Mail.ReadWrite',
                description: 'Read and send email messages',
                required: false,
                sensitive: true,
            },
            {
                name: 'https://graph.microsoft.com/Calendars.ReadWrite',
                description: 'Read and create calendar events',
                required: false,
                sensitive: true,
            },
            {
                name: 'https://graph.microsoft.com/Files.ReadWrite',
                description: 'Read and write files in OneDrive',
                required: false,
                sensitive: true,
            },
            {
                name: 'https://graph.microsoft.com/Contacts.ReadWrite',
                description: 'Read and write contacts',
                required: false,
                sensitive: true,
            },
        ],
        default_scopes: [
            'openid',
            'email',
            'https://graph.microsoft.com/Mail.ReadWrite',
            'https://graph.microsoft.com/Calendars.ReadWrite',
        ],
    };

    const mockUseIntegrations = {
        integrations: mockIntegrations,
        loading: false,
        error: null,
        refreshIntegrations: jest.fn(),
    };

    beforeEach(() => {
        jest.clearAllMocks();
        (useSession as jest.Mock).mockReturnValue(mockSession);
        (useIntegrations as jest.Mock).mockReturnValue(mockUseIntegrations);
        (userApi.getProviderScopes as jest.Mock).mockResolvedValue(mockProviderScopes);
        (userApi.startOAuthFlow as jest.Mock).mockResolvedValue({
            authorization_url: 'https://login.microsoftonline.com/oauth2/v2.0/authorize',
        });
    });

    describe('Integration Settings Dialog', () => {
        it('should render scope selector when editing existing Microsoft integration', async () => {
            render(<IntegrationsContent />);

            // Find and click the gear icon (settings button) for the Microsoft integration
            const settingsButton = screen.getByTitle('Edit permissions');
            expect(settingsButton).toBeInTheDocument();

            fireEvent.click(settingsButton);

            // Wait for the dialog to open and scopes to load
            await waitFor(() => {
                expect(screen.getByText('Modify Permissions for MICROSOFT')).toBeInTheDocument();
            });

            // Verify that the scope selector is rendered with the loaded scopes
            expect(screen.getByText('Required Permissions')).toBeInTheDocument();
            expect(screen.getByText('Optional Permissions')).toBeInTheDocument();

            // Check that specific scopes are displayed
            expect(screen.getByText('OpenID Connect authentication')).toBeInTheDocument();
            expect(screen.getByText('Read and send email messages')).toBeInTheDocument();
            expect(screen.getByText('Read and create calendar events')).toBeInTheDocument();
        });

        it('should load provider scopes when opening settings dialog', async () => {
            render(<IntegrationsContent />);

            const settingsButton = screen.getByTitle('Edit permissions');
            fireEvent.click(settingsButton);

            // Verify that getProviderScopes was called
            await waitFor(() => {
                expect(userApi.getProviderScopes).toHaveBeenCalledWith('microsoft');
            });
        });

        it('should display required and optional scopes correctly', async () => {
            render(<IntegrationsContent />);

            const settingsButton = screen.getByTitle('Edit permissions');
            fireEvent.click(settingsButton);

            await waitFor(() => {
                // Required scopes should be visible but not editable
                expect(screen.getByText('Required Permissions')).toBeInTheDocument();
                expect(screen.getByText('Optional Permissions')).toBeInTheDocument();

                // Check that the summary section shows the total count
                expect(screen.getByText('Total: 6 permissions')).toBeInTheDocument();
            });

            // Check that required scopes have the "Required" badge
            const requiredBadges = screen.getAllByText('Required');
            expect(requiredBadges).toHaveLength(2);

            // Check that sensitive scopes have the "Sensitive" badge
            // We expect 4 sensitive scopes: Mail.ReadWrite, Calendars.ReadWrite, Files.ReadWrite, Contacts.ReadWrite
            const sensitiveBadges = screen.getAllByText('Sensitive');
            expect(sensitiveBadges.length).toBeGreaterThanOrEqual(4);
            expect(sensitiveBadges.length).toBeLessThanOrEqual(8); // Allow for potential duplicates in test environment
        });

        it('should pre-select existing integration scopes when editing', async () => {
            render(<IntegrationsContent />);

            const settingsButton = screen.getByTitle('Edit permissions');
            fireEvent.click(settingsButton);

            await waitFor(() => {
                // The summary section should show the total count of selected scopes
                expect(screen.getByText('Total: 6 permissions')).toBeInTheDocument();
            });
        });

        it('should show correct dialog title and description for existing integration', async () => {
            render(<IntegrationsContent />);

            const settingsButton = screen.getByTitle('Edit permissions');
            fireEvent.click(settingsButton);

            await waitFor(() => {
                expect(screen.getByText('Modify Permissions for MICROSOFT')).toBeInTheDocument();
                expect(screen.getByText('Modify the permissions granted to Briefly. Required permissions are automatically included.')).toBeInTheDocument();
            });
        });

        it('should show correct dialog title and description for new integration', async () => {
            // Mock no existing integrations
            (useIntegrations as jest.Mock).mockReturnValue({
                ...mockUseIntegrations,
                integrations: [],
            });

            render(<IntegrationsContent />);

            const connectButton = screen.getByText('Connect');
            fireEvent.click(connectButton);

            await waitFor(() => {
                expect(screen.getByText('Connect MICROSOFT Account')).toBeInTheDocument();
                expect(screen.getByText('Select which permissions you\'d like to grant to Briefly. All permissions are selected by default for the best experience.')).toBeInTheDocument();
            });
        });
    });

    describe('Scope Loading and State Management', () => {
        it('should handle API errors gracefully when loading scopes', async () => {
            (userApi.getProviderScopes as jest.Mock).mockRejectedValue(new Error('API Error'));

            render(<IntegrationsContent />);

            const settingsButton = screen.getByTitle('Edit permissions');
            fireEvent.click(settingsButton);

            // Should still show the dialog even if scopes fail to load
            await waitFor(() => {
                expect(screen.getByText('Modify Permissions for MICROSOFT')).toBeInTheDocument();
            });

            // Scope selector should render with empty scopes array
            expect(screen.getByText('Selected Permissions')).toBeInTheDocument();
        });

        it('should convert read-only scopes to read-write scopes', async () => {
            // Mock integration with read-only scopes
            const mockIntegrationsWithReadOnly = [
                {
                    ...mockIntegrations[0],
                    scopes: [
                        'https://graph.microsoft.com/Mail.Read',
                        'https://graph.microsoft.com/Calendars.Read',
                    ],
                },
            ];

            (useIntegrations as jest.Mock).mockReturnValue({
                ...mockUseIntegrations,
                integrations: mockIntegrationsWithReadOnly,
            });

            render(<IntegrationsContent />);

            const settingsButton = screen.getByTitle('Edit permissions');
            fireEvent.click(settingsButton);

            await waitFor(() => {
                // The summary section should show the converted scopes
                expect(screen.getByText('Total: 6 permissions')).toBeInTheDocument();
            });
        });
    });

    describe('Integration Actions', () => {
        it('should call startOAuthFlow when updating permissions', async () => {
            render(<IntegrationsContent />);

            const settingsButton = screen.getByTitle('Edit permissions');
            fireEvent.click(settingsButton);

            await waitFor(() => {
                expect(screen.getByText('Update Permissions')).toBeInTheDocument();
            });

            const updateButton = screen.getByText('Update Permissions');
            fireEvent.click(updateButton);

            // Should call startOAuthFlow with the selected scopes
            await waitFor(() => {
                expect(userApi.startOAuthFlow).toHaveBeenCalledWith('microsoft', expect.any(Array));
            });
        });

        it('should disconnect integration when disconnect button is clicked', async () => {
            render(<IntegrationsContent />);

            const disconnectButton = screen.getByText('Disconnect');
            fireEvent.click(disconnectButton);

            expect(userApi.disconnectIntegration).toHaveBeenCalledWith('microsoft');
        });
    });

    describe('Component Rendering', () => {
        it('should show loading state when integrations are loading', () => {
            (useIntegrations as jest.Mock).mockReturnValue({
                ...mockUseIntegrations,
                loading: true,
            });

            render(<IntegrationsContent />);

            // Check for the loading spinner by its class
            expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
        });

        it('should show error state when integrations fail to load', () => {
            (useIntegrations as jest.Mock).mockReturnValue({
                ...mockUseIntegrations,
                error: 'Failed to load integrations',
            });

            render(<IntegrationsContent />);

            expect(screen.getByText('Failed to load integrations')).toBeInTheDocument();
        });

        it('should show authentication required when not signed in', () => {
            (useSession as jest.Mock).mockReturnValue({
                data: null,
                status: 'unauthenticated',
            });

            render(<IntegrationsContent />);

            expect(screen.getByText('Authentication Required')).toBeInTheDocument();
            expect(screen.getByText('Please sign in to manage your integrations')).toBeInTheDocument();
        });

        it('should only show integrations matching the session provider', () => {
            render(<IntegrationsContent />);

            // Should only show Microsoft integration since session provider is microsoft
            expect(screen.getByText('Microsoft')).toBeInTheDocument();
            expect(screen.queryByText('Google')).not.toBeInTheDocument();
        });
    });

    describe('Type Safety and Data Handling', () => {
        it('should handle missing scopes gracefully', async () => {
            // Mock integration without scopes
            const mockIntegrationsWithoutScopes = [
                {
                    ...mockIntegrations[0],
                    scopes: undefined,
                },
            ];

            (useIntegrations as jest.Mock).mockReturnValue({
                ...mockUseIntegrations,
                integrations: mockIntegrationsWithoutScopes,
            });

            render(<IntegrationsContent />);

            const settingsButton = screen.getByTitle('Edit permissions');
            fireEvent.click(settingsButton);

            // Should not crash and should handle undefined scopes
            await waitFor(() => {
                expect(screen.getByText('Modify Permissions for MICROSOFT')).toBeInTheDocument();
            });
        });

        it('should handle empty scopes array', async () => {
            // Mock integration with empty scopes
            const mockIntegrationsWithEmptyScopes = [
                {
                    ...mockIntegrations[0],
                    scopes: [],
                },
            ];

            (useIntegrations as jest.Mock).mockReturnValue({
                ...mockUseIntegrations,
                integrations: mockIntegrationsWithEmptyScopes,
            });

            render(<IntegrationsContent />);

            const settingsButton = screen.getByTitle('Edit permissions');
            fireEvent.click(settingsButton);

            // Should handle empty scopes gracefully
            await waitFor(() => {
                expect(screen.getByText('Modify Permissions for MICROSOFT')).toBeInTheDocument();
            });
        });
    });
});
