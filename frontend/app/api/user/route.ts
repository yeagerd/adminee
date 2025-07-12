import { getServerSession } from 'next-auth/next';
import { NextRequest, NextResponse } from 'next/server';
import { authOptions } from '../../../lib/auth';
import { env, validateUserServiceEnv } from '../../../lib/env';

// Validate user service environment variables
validateUserServiceEnv();

export async function GET() {
    try {
        const session = await getServerSession(authOptions);

        if (!session?.user?.id) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }

        const response = await fetch(`${env.USER_SERVICE_URL}/users/${session.user.id}`, {
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': env.API_FRONTEND_USER_KEY,
            },
        });

        if (!response.ok) {
            const errorText = await response.text();
            return NextResponse.json(
                { error: `User service error: ${errorText}` },
                { status: response.status }
            );
        }

        const userData = await response.json();
        return NextResponse.json(userData);
    } catch (error) {
        console.error('User API error:', error);
        return NextResponse.json(
            { error: 'Internal server error' },
            { status: 500 }
        );
    }
}

export async function PUT(request: NextRequest) {
    try {
        const session = await getServerSession(authOptions);

        if (!session?.user?.id) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }

        const body = await request.json();

        const response = await fetch(`${env.USER_SERVICE_URL}/users/${session.user.id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': env.API_FRONTEND_USER_KEY,
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

        const userData = await response.json();
        return NextResponse.json(userData);
    } catch (error) {
        console.error('User API error:', error);
        return NextResponse.json(
            { error: 'Internal server error' },
            { status: 500 }
        );
    }
} 