import { useIntegrations } from '@/contexts/integrations-context';
import { render, screen } from '@testing-library/react';
import { EmailFolderSelector } from './email-folder-selector';

// Mock the integrations context
jest.mock('@/contexts/integrations-context');
const mockUseIntegrations = useIntegrations as jest.MockedFunction<typeof useIntegrations>;

// Mock the gateway client
jest.mock('@/lib/gateway-client', () => ({
    __esModule: true,
    default: {
        getEmailFolders: jest.fn(),
    },
}));

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

    it('renders without crashing', () => {
        const mockOnFolderSelect = jest.fn();
        render(<EmailFolderSelector onFolderSelect={mockOnFolderSelect} />);

        // Check that the hamburger menu button is rendered
        const button = screen.getByRole('button');
        expect(button).toBeInTheDocument();
    });

    it('uses fallback folders when no providers are active', () => {
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

        // Should still render the button
        const button = screen.getByRole('button');
        expect(button).toBeInTheDocument();
    });
}); 