import { headers } from 'next/headers';
import { NextRequest, NextResponse } from 'next/server';

interface WebhookPayload {
    type: string;
    data: {
        email: string;
        provider: 'google' | 'microsoft';
        providerUserId: string;
        name: {
            first: string;
            last: string;
        };
        picture?: string;
        accessToken?: string;
        refreshToken?: string;
        expiresAt?: number;
    };
    timestamp: number;
}

export async function POST(request: NextRequest) {
    try {
        // Verify webhook signature
        const headersList = await headers();
        const signature = headersList.get('x-webhook-signature');
        const expectedSignature = process.env.BFF_WEBHOOK_SECRET;

        if (!signature || signature !== expectedSignature) {
            return NextResponse.json(
                { error: 'Invalid webhook signature' },
                { status: 401 }
            );
        }

        const payload: WebhookPayload = await request.json();

        if (payload.type === 'oauth.user_authenticated') {
            // Call user service to create or update user
            const userServiceUrl = `${process.env.USER_SERVICE_URL}/users/`;

            const userData = {
                external_auth_id: payload.data.providerUserId,
                auth_provider: payload.data.provider,
                email: payload.data.email,
                first_name: payload.data.name.first,
                last_name: payload.data.name.last,
                profile_image_url: payload.data.picture || null,
            };

            const response = await fetch(userServiceUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': process.env.USER_SERVICE_API_KEY || '',
                },
                body: JSON.stringify(userData),
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error('User service error:', errorText);
                return NextResponse.json(
                    { error: 'Failed to create/update user', details: errorText },
                    { status: response.status }
                );
            }

            const user = await response.json();

            // If OAuth tokens are provided, store them via user service integration endpoints
            if (payload.data.accessToken) {
                try {
                    const integrationData = {
                        provider: payload.data.provider,
                        access_token: payload.data.accessToken,
                        refresh_token: payload.data.refreshToken,
                        expires_at: payload.data.expiresAt,
                    };

                    const integrationUrl = `${process.env.USER_SERVICE_URL}/users/${user.id}/integrations`;
                    const integrationResponse = await fetch(integrationUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-API-Key': process.env.USER_SERVICE_API_KEY || '',
                        },
                        body: JSON.stringify(integrationData),
                    });

                    if (!integrationResponse.ok) {
                        console.error('Failed to store OAuth tokens:', await integrationResponse.text());
                    }
                } catch (error) {
                    console.error('Error storing OAuth tokens:', error);
                }
            }

            return NextResponse.json({
                success: true,
                user: user,
                message: 'User created/updated successfully'
            });
        }

        return NextResponse.json(
            { error: 'Unknown webhook type' },
            { status: 400 }
        );

    } catch (error) {
        console.error('Webhook processing error:', error);
        return NextResponse.json(
            { error: 'Internal server error' },
            { status: 500 }
        );
    }
} 