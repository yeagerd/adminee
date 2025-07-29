import { render, screen } from '@testing-library/react';
import EmailFolderSelector, { DEFAULT_FOLDERS } from './email-folder-selector';

// Mock the integrations context
jest.mock('@/contexts/integrations-context', () => ({
    useIntegrations: () => ({
        integrations: [
            { provider: 'google', status: 'active' },
            { provider: 'microsoft', status: 'active' }
        ]
    })
}));

describe('EmailFolderSelector', () => {
    const mockOnFolderSelect = jest.fn();

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('renders the folder selector button', () => {
        render(<EmailFolderSelector onFolderSelect={mockOnFolderSelect} />);
        expect(screen.getByRole('button')).toBeInTheDocument();
    });

    it('has the correct default folders defined', () => {
        expect(DEFAULT_FOLDERS).toHaveLength(5);
        expect(DEFAULT_FOLDERS[0].id).toBe('inbox');
        expect(DEFAULT_FOLDERS[0].name).toBe('Inbox');
        expect(DEFAULT_FOLDERS[1].id).toBe('sent');
        expect(DEFAULT_FOLDERS[1].name).toBe('Sent');
        expect(DEFAULT_FOLDERS[2].id).toBe('draft');
        expect(DEFAULT_FOLDERS[2].name).toBe('Drafts');
        expect(DEFAULT_FOLDERS[3].id).toBe('spam');
        expect(DEFAULT_FOLDERS[3].name).toBe('Spam');
        expect(DEFAULT_FOLDERS[4].id).toBe('trash');
        expect(DEFAULT_FOLDERS[4].name).toBe('Trash');
    });

    it('renders with custom folders when provided', () => {
        const customFolders = [
            {
                id: 'custom1',
                name: 'Custom Folder 1',
                icon: <span>📁</span>,
                label: 'custom1'
            }
        ];

        render(
            <EmailFolderSelector
                onFolderSelect={mockOnFolderSelect}
                customFolders={customFolders}
            />
        );

        expect(screen.getByRole('button')).toBeInTheDocument();
    });
}); 