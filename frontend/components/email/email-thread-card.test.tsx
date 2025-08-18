import { EmailMessage, Provider } from "@/types";
import { render, screen } from '@testing-library/react';
import { useRouter } from 'next/navigation';
import React from 'react';
import EmailThreadCard from './email-thread-card';

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
    useRouter: jest.fn(),
}));

// Mock hooks used inside the component to avoid network and side effects
jest.mock('@/hooks/use-shipment-detection', () => ({
    useShipmentDetection: () => ({ trackingNumbers: [] })
}));

jest.mock('@/hooks/use-shipment-events', () => ({
    useShipmentEvents: () => ({ data: [], hasEvents: false })
}));

jest.mock('sonner', () => ({ toast: { success: jest.fn() } }));

jest.mock('next-auth/react', () => ({
    __esModule: true,
    useSession: () => ({ data: null, status: 'unauthenticated' }),
    signIn: jest.fn(),
    signOut: jest.fn(),
    SessionProvider: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
}));

const mockRouter = {
    push: jest.fn(),
    replace: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn(),
    prefetch: jest.fn(),
};

const baseEmail: EmailMessage = {
    id: 'test-id',
    thread_id: 'thread-1',
    subject: 'Test Subject',
    snippet: 'Snippet',
    body_text: '',
    body_html: '',
    from_address: { email: 'sender@example.com', name: 'Sender Name' },
    to_addresses: [{ email: 'recipient@example.com', name: 'Recipient Name' }],
    cc_addresses: [],
    bcc_addresses: [],
    date: new Date().toISOString(),
    labels: [],
    is_read: true,
    has_attachments: false,
    provider: Provider.MICROSOFT,
    provider_message_id: 'pmid',
    account_email: 'user@example.com',
    account_name: 'User'
};

describe('EmailThreadCard rendering', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        (useRouter as jest.Mock).mockReturnValue(mockRouter);
    });

    it('renders simple HTML body without toggle', () => {
        const simpleHtml = '<html><body><div>Try it out today!</div></body></html>';
        render(
            <EmailThreadCard
                email={{ ...baseEmail, body_html: simpleHtml, body_text: '' }}
                isSelected
            />
        );

        expect(screen.getByText('Try it out today!')).toBeInTheDocument();
        expect(screen.queryByText(/Show quoted text/i)).not.toBeInTheDocument();
    });

    it('renders quoted-only HTML directly without toggle', () => {
        // Example provided by user (anonymized already)
        const quotedOnlyHtml = "<html><head>\r\n<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\"><style type=\"text/css\" style=\"display:none\">\r\n<!--\r\np\r\n\t{margin-top:0;\r\n\tmargin-bottom:0}\r\n-->\r\n</style></head><body dir=\"ltr\"><div class=\"elementToProof\" style=\"font-family:Aptos,Aptos_EmbeddedFont,Aptos_MSFontService,Calibri,Helvetica,sans-serif; font-size:12pt; color:rgb(0,0,0)\">Try it out today!</div></body></html>";

        render(
            <EmailThreadCard
                email={{ ...baseEmail, body_html: quotedOnlyHtml, body_text: '' }}
                isSelected
            />
        );

        // We should see the content rendered and no toggle, meaning it rendered directly
        expect(screen.getByText('Try it out today!')).toBeInTheDocument();
        expect(screen.queryByText(/Show quoted text/i)).not.toBeInTheDocument();
    });

    it('does not split content with Outlook-style headers in the middle of email body', () => {
        // This simulates the user's issue where Outlook-style headers appear in the middle
        // of legitimate email content and should NOT be treated as quoted content
        // The headers are not in the exact format that indicates quoted content
        const emailWithHeadersInBody = `
      <div>I can't wait to try it out!</div>
      <div>Please note: From: Dan . &lt;danstrashbin@hotmail.com&gt;</div>
      <div>Sent: Wednesday, July 30, 2025 5:03 PM</div>
      <div>To: Try Briefly &lt;trybriefly@outlook.com&gt;</div>
      <div>Subject: Re: Hello from Briefly</div>
      <div>Try it out today!</div>
    `;

        render(
            <EmailThreadCard
                email={{ ...baseEmail, body_html: emailWithHeadersInBody, body_text: '' }}
                isSelected
            />
        );

        // The content should be rendered as a single piece without splitting
        expect(screen.getByText("I can't wait to try it out!")).toBeInTheDocument();
        expect(screen.getByText('Try it out today!')).toBeInTheDocument();
        expect(screen.queryByText(/Show quoted text/i)).not.toBeInTheDocument();
    });

    it('renders content with Outlook-style headers as single piece when not in quoted format', () => {
        // This simulates an email that contains Outlook-style headers but they are not
        // in the exact format that indicates quoted content
        const emailWithHeaders = `
      <div>Here's my response to your email.</div>
      <div>From: Dan . &lt;danstrashbin@hotmail.com&gt;</div>
      <div>Sent: Wednesday, July 30, 2025 5:03 PM</div>
      <div>To: Try Briefly &lt;trybriefly@outlook.com&gt;</div>
      <div>Subject: Re: Hello from Briefly</div>
      <div>I can't wait to try it out!</div>
    `;

        render(
            <EmailThreadCard
                email={{ ...baseEmail, body_html: emailWithHeaders, body_text: '' }}
                isSelected
            />
        );

        // The content should be rendered as a single piece without splitting
        expect(screen.getByText("Here's my response to your email.")).toBeInTheDocument();
        expect(screen.getByText("I can't wait to try it out!")).toBeInTheDocument();
        expect(screen.queryByText(/Show quoted text/i)).not.toBeInTheDocument();
    });

    it('does not split content with CC and BCC fields in the middle of email body', () => {
        // This simulates an email that contains CC/BCC fields in the middle
        // of legitimate email content and should NOT be treated as quoted content
        const emailWithCCBCCInBody = `
             <div>Here's my response to your email.</div>
             <div>CC: colleague@example.com</div>
             <div>BCC: manager@example.com</div>
             <div>From: Dan . &lt;danstrashbin@hotmail.com&gt;</div>
             <div>Sent: Wednesday, July 30, 2025 5:03 PM</div>
             <div>To: Try Briefly &lt;trybriefly@outlook.com&gt;</div>
             <div>Subject: Re: Hello from Briefly</div>
             <div>I can't wait to try it out!</div>
         `;

        render(
            <EmailThreadCard
                email={{ ...baseEmail, body_html: emailWithCCBCCInBody, body_text: '' }}
                isSelected
            />
        );

        // The content should be rendered as a single piece without splitting
        expect(screen.getByText("Here's my response to your email.")).toBeInTheDocument();
        expect(screen.getByText("I can't wait to try it out!")).toBeInTheDocument();
        expect(screen.queryByText(/Show quoted text/i)).not.toBeInTheDocument();
    });

    it('does not split content with mixed email headers in the middle of email body', () => {
        // This simulates an email that contains various email header fields
        // scattered throughout the content, which should NOT be treated as quoted content
        const emailWithMixedHeadersInBody = `
             <div>Here's my response to your email.</div>
             <div>From: Dan . &lt;danstrashbin@hotmail.com&gt;</div>
             <div>Some additional content here.</div>
             <div>CC: colleague@example.com</div>
             <div>More content in the middle.</div>
             <div>Sent: Wednesday, July 30, 2025 5:03 PM</div>
             <div>To: Try Briefly &lt;trybriefly@outlook.com&gt;</div>
             <div>Subject: Re: Hello from Briefly</div>
             <div>BCC: manager@example.com</div>
             <div>I can't wait to try it out!</div>
         `;

        render(
            <EmailThreadCard
                email={{ ...baseEmail, body_html: emailWithMixedHeadersInBody, body_text: '' }}
                isSelected
            />
        );

        // The content should be rendered as a single piece without splitting
        expect(screen.getByText("Here's my response to your email.")).toBeInTheDocument();
        expect(screen.getByText("Some additional content here.")).toBeInTheDocument();
        expect(screen.getByText("More content in the middle.")).toBeInTheDocument();
        expect(screen.getByText("I can't wait to try it out!")).toBeInTheDocument();
        expect(screen.queryByText(/Show quoted text/i)).not.toBeInTheDocument();
    });

    it('does not split content with email headers in different HTML elements', () => {
        // This simulates an email where headers appear in different HTML elements
        // which should NOT be treated as quoted content
        const emailWithHeadersInDifferentElements = `
             <p>Here's my response to your email.</p>
             <span>From: Dan . &lt;danstrashbin@hotmail.com&gt;</span>
             <div>Sent: Wednesday, July 30, 2025 5:03 PM</div>
             <strong>To: Try Briefly &lt;trybriefly@outlook.com&gt;</strong>
             <em>Subject: Re: Hello from Briefly</em>
             <p>I can't wait to try it out!</p>
         `;

        render(
            <EmailThreadCard
                email={{ ...baseEmail, body_html: emailWithHeadersInDifferentElements, body_text: '' }}
                isSelected
            />
        );

        // The content should be rendered as a single piece without splitting
        expect(screen.getByText("Here's my response to your email.")).toBeInTheDocument();
        expect(screen.getByText("I can't wait to try it out!")).toBeInTheDocument();
        expect(screen.queryByText(/Show quoted text/i)).not.toBeInTheDocument();
    });

    it('does not split content with email headers in table cells', () => {
        // This simulates an email where headers appear in table cells
        // which should NOT be treated as quoted content
        const emailWithHeadersInTable = `
             <div>Here's my response to your email.</div>
             <table>
                 <tr><td>From: Dan . &lt;danstrashbin@hotmail.com&gt;</td></tr>
                 <tr><td>Sent: Wednesday, July 30, 2025 5:03 PM</td></tr>
                 <tr><td>To: Try Briefly &lt;trybriefly@outlook.com&gt;</td></tr>
                 <tr><td>Subject: Re: Hello from Briefly</td></tr>
             </table>
             <div>I can't wait to try it out!</div>
         `;

        render(
            <EmailThreadCard
                email={{ ...baseEmail, body_html: emailWithHeadersInTable, body_text: '' }}
                isSelected
            />
        );

        // The content should be rendered as a single piece without splitting
        expect(screen.getByText("Here's my response to your email.")).toBeInTheDocument();
        expect(screen.getByText("I can't wait to try it out!")).toBeInTheDocument();
        expect(screen.queryByText(/Show quoted text/i)).not.toBeInTheDocument();
    });
});