import { authOptions } from '@/lib/auth';
import { getServerSession } from 'next-auth/next';
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
    try {
        const USER_SERVICE_URL = process.env.USER_SERVICE_URL;

        if (!USER_SERVICE_URL) {
            return NextResponse.json({ error: 'USER_SERVICE_URL environment variable is required' }, { status: 500 });
        }

        const session = await getServerSession(authOptions);

        if (!session?.user?.id || !session?.accessToken) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }

        const body = await request.json();

        const response = await fetch(`${USER_SERVICE_URL}/users/${session.user.id}/integrations/oauth/start`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${session.accessToken}`,
            },
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            const errorText = await response.text();
            return NextResponse.json(
                { error: `User service error: ${errorText}` },
                { status: response.status }
            );
        }

        const oauthData = await response.json();
        return NextResponse.json(oauthData);
    } catch (error) {
        console.error('OAuth start API error:', error);
        return NextResponse.json(
            { error: 'Internal server error' },
            { status: 500 }
        );
    }
} 