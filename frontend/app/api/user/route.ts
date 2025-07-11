import { authOptions } from '@/lib/auth';
import { getServerSession } from 'next-auth/next';
import { NextRequest, NextResponse } from 'next/server';

export async function GET() {
    try {
        const USER_SERVICE_URL = process.env.USER_SERVICE_URL;
        const API_FRONTEND_USER_KEY = process.env.API_FRONTEND_USER_KEY;

        if (!USER_SERVICE_URL) {
            return NextResponse.json({ error: 'USER_SERVICE_URL environment variable is required' }, { status: 500 });
        }
        if (!API_FRONTEND_USER_KEY) {
            return NextResponse.json({ error: 'API_FRONTEND_USER_KEY environment variable is required' }, { status: 500 });
        }

        const session = await getServerSession(authOptions);

        if (!session?.user?.id) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }

        const response = await fetch(`${USER_SERVICE_URL}/users/${session.user.id}`, {
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': API_FRONTEND_USER_KEY,
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
        const USER_SERVICE_URL = process.env.USER_SERVICE_URL;
        const API_FRONTEND_USER_KEY = process.env.API_FRONTEND_USER_KEY;

        if (!USER_SERVICE_URL) {
            return NextResponse.json({ error: 'USER_SERVICE_URL environment variable is required' }, { status: 500 });
        }
        if (!API_FRONTEND_USER_KEY) {
            return NextResponse.json({ error: 'API_FRONTEND_USER_KEY environment variable is required' }, { status: 500 });
        }

        const session = await getServerSession(authOptions);

        if (!session?.user?.id) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }

        const body = await request.json();

        const response = await fetch(`${USER_SERVICE_URL}/users/${session.user.id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': API_FRONTEND_USER_KEY,
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