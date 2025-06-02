import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';
import { NextResponse } from 'next/server';

// Define public routes that do not require authentication
const isPublicRoute = createRouteMatcher([
  '/', // Example: landing page
  '/login(.*)',
  '/sign-up(.*)',
  '/api/webhooks/(.*)', // Example: public API endpoint
]);

export default clerkMiddleware(async (auth, req) => {
  // If the route is not public, then protect it.
  // auth().protect() will redirect unauthenticated users to the sign-in page for web pages
  // or return a 403/404 for API routes.
  if (!isPublicRoute(req)) {
    await auth.protect(); // Call protect directly on the auth object from middleware params
  }
  // No explicit NextResponse.next() needed if auth().protect() is called and handles the response/redirect,
  // but if it doesn't redirect (i.e., user is authenticated), then we should proceed.
  // However, the more robust pattern is to always return a response from middleware.
  // So, if protect() doesn't throw/redirect, we will reach here if the user is authenticated.
  // If it's a public route, we also reach here.
  // For now, let's rely on protect() to handle unauthenticated and let authenticated pass, implicitly calling next().
  // A more explicit way would be to check userId after `const { userId } = await auth();` 
  // and then decide to call next() or redirect.
});

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    '/((?!_next|[^?]*\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes
    '/(api|trpc)(.*)',
  ],
}; 