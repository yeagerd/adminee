import { getServerSession } from 'next-auth';
import { NextRequest, NextResponse } from 'next/server';
import { authOptions } from '../../../lib/auth';
import { env, validateChatServiceEnv } from '../../../lib/env';

// Validate chat service environment variables
validateChatServiceEnv();

export async function POST(request: NextRequest) {
    try {
        // Verify user is authenticated
        const session = await getServerSession(authOptions);
        if (!session?.user?.email || !session?.user?.id) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }

        const body = await request.json();

        // Forward request to chat service with API key authentication
        const response = await fetch(`${env.CHAT_SERVICE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${env.API_FRONTEND_CHAT_KEY}`,
                'X-User-Email': session.user.email,
            },
            body: JSON.stringify({
                ...body,
                user_id: session.user.id,
            }),
        });

        if (!response.ok) {
            const errorData = await response.text();
            console.error('Chat service error:', response.status, errorData);
            return NextResponse.json(
                { error: 'Chat service error' },
                { status: response.status }
            );
        }

        const data = await response.json();
        return NextResponse.json(data);

    } catch (error) {
        console.error('Chat API error:', error);
        return NextResponse.json(
            { error: 'Internal server error' },
            { status: 500 }
        );
    }
}

export async function GET() {
    try {
        // Verify user is authenticated
        const session = await getServerSession(authOptions);
        if (!session?.user?.email) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }

        // Forward request to chat service with API key authentication
        const response = await fetch(`${env.CHAT_SERVICE_URL}/chat`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${env.API_FRONTEND_CHAT_KEY}`,
                'X-User-Email': session.user.email,
            },
        });

        if (!response.ok) {
            const errorData = await response.text();
            console.error('Chat service error:', response.status, errorData);
            return NextResponse.json(
                { error: 'Chat service error' },
                { status: response.status }
            );
        }

        const data = await response.json();
        return NextResponse.json(data);

    } catch (error) {
        console.error('Chat API error:', error);
        return NextResponse.json(
            { error: 'Internal server error' },
            { status: 500 }
        );
    }
} 