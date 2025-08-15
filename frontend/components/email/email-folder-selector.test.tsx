import { useIntegrations } from '@/contexts/integrations-context';
import { render, screen, waitFor } from '@testing-library/react';
import { EmailFolderSelector } from './email-folder-selector';

// Mock the integrations context
jest.mock('@/contexts/integrations-context');
const mockUseIntegrations = useIntegrations as jest.MockedFunction<typeof useIntegrations>;

// Mock the gateway client with default and named exports
jest.mock('@/lib/gateway-client', () => {
    const mockGetEmailFolders = jest.fn().mockResolvedValue({ success: true, data: { folders: [] } });
    return {
        __esModule: true,
        default: { getEmailFolders: mockGetEmailFolders },
        gatewayClient: { getEmailFolders: mockGetEmailFolders },
        GatewayClient: class {},
    };
});

describe('EmailFolderSelector', () => {
    beforeEach(() => {
        mockUseIntegrations.mockReturnValue({
            integrations: [],
            activeProviders: ['google'],
            loading: false,
            error: null,
            hasExpiredButRefreshableTokens: false,
            refreshIntegrations: jest.fn(),
            triggerAutoRefreshIfNeeded: jest.fn(),
        });
    });

    it('renders without crashing', async () => {
        const mockOnFolderSelect = jest.fn();
        render(<EmailFolderSelector onFolderSelect={mockOnFolderSelect} />);

        await waitFor(() => {
            const button = screen.getByRole('button');
            expect(button).toBeInTheDocument();
        });
    });

    it('uses fallback folders when no providers are active', async () => {
        mockUseIntegrations.mockReturnValue({
            integrations: [],
            activeProviders: [],
            loading: false,
            error: null,
            hasExpiredButRefreshableTokens: false,
            refreshIntegrations: jest.fn(),
            triggerAutoRefreshIfNeeded: jest.fn(),
        });

        const mockOnFolderSelect = jest.fn();
        render(<EmailFolderSelector onFolderSelect={mockOnFolderSelect} />);

        await waitFor(() => {
            const button = screen.getByRole('button');
            expect(button).toBeInTheDocument();
        });
    });
}); 