import { EmailMessage } from '@/types/office-service';
import React from 'react';
import EmailCard from './email-card';

interface EmailThreadProps {
    thread: {
        id: string;
        emails: EmailMessage[];
    };
}

const EmailThread: React.FC<EmailThreadProps> = ({ thread }) => {
    return (
        <div className="mb-6">
            {thread.emails.map((email) => (
                <EmailCard key={email.id} email={email} />
            ))}
        </div>
    );
};

export default EmailThread; 