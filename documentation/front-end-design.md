# Frontend Design: Architecture and Navigation Flow

## 1. Core Technologies & Structure
*   **Next.js App Router:** We'll continue using the App Router conventions within the `src/app` directory.
*   **Route Groups:** To organize routes and apply specific layouts or logic, we can use route groups:
    *   `(auth)`: For authentication-related pages (login, signup).
    *   `(onboarding)`: For the user onboarding flow.
    *   `(main)`: For the main application experience post-login/onboarding (dashboard, settings).
    *   `(public)`: For public-facing pages like a landing page, if needed in the future.
*   **Middleware:** `src/middleware.ts` (leveraging NextAuth.js) will be crucial for protecting routes and redirecting users based on their authentication and onboarding status.

## 2. Navigation Flow

*   **Unauthenticated User (New or Logged Out):**
    1.  Accesses the site (e.g., root `/` or `/dashboard`).
    2.  Middleware intercepts and redirects to `/login` (or your NextAuth sign-in page).
    3.  User signs in/signs up via NextAuth.

*   **Authenticated User - Needs Onboarding:**
    1.  After successful login, NextAuth redirects back to the app.
    2.  Middleware checks if the user has completed onboarding.
    3.  If onboarding is not complete, redirect to `/onboarding`.
    4.  User completes the onboarding steps. Onboarding might involve setting initial preferences, connecting their calendar provider, etc.
    5.  Upon completion of onboarding, redirect to `/dashboard`.

*   **Authenticated User - Onboarding Complete:**
    1.  Accesses the site or logs in.
    2.  Middleware checks auth status (authenticated) and onboarding status (complete).
    3.  User is directed to `/dashboard`.
    4.  From the dashboard, the user can navigate to:
        *   `/settings`
        *   Other features accessible via the main application layout.

## 3. Directory Structure (Illustrative)

```
frontend/src/
├── app/
│   ├── (auth)/                // Authentication-related routes
│   │   ├── login/
│   │   │   └── page.tsx
│   │   ├── sign-up/           // Example, if using NextAuth's hosted pages, these might not be custom
│   │   │   └── page.tsx
│   │   └── layout.tsx         // Optional: Layout specific to auth pages
│   ├── (onboarding)/          // Onboarding flow
│   │   ├── onboarding/
│   │   │   └── page.tsx
│   │   └── layout.tsx         // Layout for the onboarding process
│   ├── (main)/                // Main application routes (protected)
│   │   ├── dashboard/
│   │   │   └── page.tsx
│   │   ├── settings/
│   │   │   └── page.tsx
│   │   └── layout.tsx         // Main application layout (with nav, footer, etc.)
│   ├── layout.tsx             // Root layout
│   └── page.tsx               // Root page (could redirect or be a landing page)
├── components/
│   ├── navigation/
│   │   └── MainNav.tsx        // Component for the main app navigation
│   └── ...
├── lib/
└── middleware.ts
```

## 4. Key Files & Responsibilities

*   **`src/middleware.ts`:**
    *   Uses NextAuth.js middleware.
    *   Define `publicRoutes` (e.g., `/`, `/login`, `/sign-up`, API routes if any are public).
    *   Define logic:
        *   If user is authenticated and onboarding is not complete (this check might involve fetching a flag from your DB via an API route or using NextAuth's user metadata if onboarding status is stored there), redirect to `/onboarding`.
        *   If user is authenticated and onboarding is complete, allow access to main app routes. If they land on `/login` or `/onboarding`, redirect to `/dashboard`.
        *   If user is not authenticated and trying to access a protected route, redirect to `/login`.

*   **`src/app/(main)/layout.tsx`:**
    *   This will be the primary layout for the authenticated and onboarded user experience.
    *   It should include common UI elements like a navigation bar (e.g., `MainNav.tsx`), sidebar, and footer.
    *   It will fetch user data if necessary (e.g., using `getSession` from NextAuth).

*   **`src/app/(onboarding)/layout.tsx`:**
    *   A simpler layout, perhaps without the full app navigation, focused on the onboarding steps.

*   **`src/app/page.tsx` (Root Page):**
    *   This could be a simple landing page if you intend to have one.
    *   Alternatively, it could immediately trigger a redirect based on auth/onboarding status (though middleware often handles this more cleanly). For an MVP, middleware handling is often sufficient.
