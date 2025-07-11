import { withAuth } from 'next-auth/middleware';
import { NextResponse } from 'next/server';

export default withAuth(
    function middleware(req) {
        // Add any additional middleware logic here
        return NextResponse.next();
    },
    {
        callbacks: {
            authorized: ({ token, req }) => {
                // Define which routes require authentication
                const { pathname } = req.nextUrl;

                // Public routes that don't require authentication
                const publicRoutes = [
                    '/',
                    '/login',
                    '/auth/error',
                    '/api/auth',
                ];

                // Check if current path is public
                const isPublicRoute = publicRoutes.some(route =>
                    pathname.startsWith(route) || pathname === route
                );

                // Allow access to public routes
                if (isPublicRoute) {
                    return true;
                }

                // Require authentication for protected routes
                return !!token;
            },
        },
    }
);

export const config = {
    matcher: [
        // Skip Next.js internals and all static files
        '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
        // Protect these specific routes
        '/dashboard/:path*',
        '/profile/:path*',
        '/integrations/:path*',
        '/onboarding/:path*',
    ],
}; 