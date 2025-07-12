import { getServerSession } from 'next-auth/next';
import { NextResponse } from 'next/server';
import { authOptions } from '../../../lib/auth';
import { env } from '../../../lib/env';

export async function GET() {
    try {
        const session = await getServerSession(authOptions);

        if (!session?.user?.id || !session?.accessToken) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }

        const response = await fetch(`${env.USER_SERVICE_URL}/users/${session.user.id}/integrations`, {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${session.accessToken}`,
            },
        });

        if (!response.ok) {
            const errorText = await response.text();
            return NextResponse.json(
                { error: `User service error: ${errorText}` },
                { status: response.status }
            );
        }

        const integrations = await response.json();
        return NextResponse.json(integrations);
    } catch (error) {
        console.error('Integrations API error:', error);
        return NextResponse.json(
            { error: 'Internal server error' },
            { status: 500 }
        );
    }
} 