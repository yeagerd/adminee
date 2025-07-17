import React from 'react';
import EmailCard from './email-card';

interface EmailThreadProps {
    thread: {
        id: string;
        emails: any[];
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