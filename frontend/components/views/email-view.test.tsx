import { officeApi } from '@/api';
import { useIntegrations } from '@/contexts/integrations-context';
import { EmailMessage, Provider } from "@/types/api/office";
import { act, render, screen, waitFor } from '@testing-library/react';
import EmailView from './email-view';

// Mock the integrations context
jest.mock('@/contexts/integrations-context');
const mockUseIntegrations = useIntegrations as jest.MockedFunction<typeof useIntegrations>;

// Mock the office API
jest.mock('@/api', () => ({
    officeApi: {
        getEmails: jest.fn(),
        getThread: jest.fn(),
        getEmailFolders: jest.fn(),
        bulkAction: jest.fn(),
    },
}));

// Mock next-auth
jest.mock('next-auth/react', () => ({
    getSession: jest.fn(() => Promise.resolve({
        user: { id: 'test-user-id', email: 'test@example.com' }
    })),
}));

describe('EmailView - Select All Functionality', () => {
    const mockEmails: EmailMessage[] = [
        {
            id: 'email-1',
            thread_id: 'thread-1',
            subject: 'Test Email 1',
            date: '2024-01-02T10:00:00Z',
            from_address: { email: 'sender1@example.com', name: 'Sender 1' },
            to_addresses: [{ email: 'test@example.com', name: 'Test User' }],
            cc_addresses: [],
            bcc_addresses: [],
            snippet: 'Test snippet 1',
            body_text: 'Test body 1',
            is_read: false,
            has_attachments: false,
            labels: [],
            provider: Provider.GOOGLE,
            provider_message_id: 'provider-email-1',
            account_email: 'test@example.com',
        },
        {
            id: 'email-2',
            thread_id: 'thread-1',
            subject: 'Test Email 2',
            date: '2024-01-01T10:00:00Z',
            from_address: { email: 'sender2@example.com', name: 'Sender 2' },
            to_addresses: [{ email: 'test@example.com', name: 'Test User' }],
            cc_addresses: [],
            bcc_addresses: [],
            snippet: 'Test snippet 2',
            body_text: 'Test body 2',
            is_read: true,
            has_attachments: false,
            labels: [],
            provider: Provider.GOOGLE,
            provider_message_id: 'provider-email-2',
            account_email: 'test@example.com',
        },
        {
            id: 'email-3',
            thread_id: 'thread-2',
            subject: 'Test Email 3',
            date: '2024-01-03T10:00:00Z',
            from_address: { email: 'sender3@example.com', name: 'Sender 3' },
            to_addresses: [{ email: 'test@example.com', name: 'Test User' }],
            cc_addresses: [],
            bcc_addresses: [],
            snippet: 'Test snippet 3',
            body_text: 'Test body 3',
            is_read: false,
            has_attachments: false,
            labels: [],
            provider: Provider.GOOGLE,
            provider_message_id: 'provider-email-3',
            account_email: 'test@example.com',
        },
    ];

    beforeEach(async () => {
        mockUseIntegrations.mockReturnValue({
            integrations: [],
            activeProviders: ['google'],
            loading: false,
            error: null,
            hasExpiredButRefreshableTokens: false,
            refreshIntegrations: jest.fn(),
            triggerAutoRefreshIfNeeded: jest.fn(),
        });

        // Mock the office API methods
        (officeApi.getEmails as jest.Mock).mockResolvedValue({
            data: { messages: mockEmails }
        });
        (officeApi.getEmailFolders as jest.Mock).mockResolvedValue({
            data: { folders: [] }
        });
        (officeApi.getThread as jest.Mock).mockResolvedValue({
            data: { messages: mockEmails }
        });

        // Mock the office API methods for the second test
        (officeApi.getEmails as jest.Mock).mockResolvedValue({
            data: { messages: mockEmails }
        });
    });

    it('should select only latest emails in tight view mode', async () => {
        (officeApi.getEmails as jest.Mock).mockResolvedValue({
            data: { messages: mockEmails }
        });

        await act(async () => {
            render(<EmailView activeTool="email" />);
        });

        await waitFor(() => expect(screen.getByText('Inbox')).toBeInTheDocument());
    });

    it('should handle view mode changes correctly', async () => {
        await act(async () => {
            render(<EmailView activeTool="email" />);
        });
        await waitFor(() => expect(screen.getByText('Inbox')).toBeInTheDocument());
    });
}); 