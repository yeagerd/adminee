import { SignedIn, SignedOut } from "@clerk/nextjs";
import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import OnboardingStatus from "../components/components/OnboardingStatus"; // Adjusted path

export const dynamic = 'force-dynamic';

export default async function HomePage() {
  const { userId } = await auth();
  
  // If the user is authenticated, redirect to the dashboard
  if (userId) {
    redirect('/dashboard');
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-4">
      <h1 className="text-3xl font-bold mb-6">Welcome to Briefly</h1>
      <SignedIn>
        <p>You are signed in. Redirecting to dashboard...</p>
        <OnboardingStatus />
      </SignedIn>
      <SignedOut>
        <div className="max-w-md text-center">
          <p className="mb-6 text-gray-600">Your AI-powered calendar assistant to help you stay organized and prepared for meetings.</p>
          <a 
            href="/login" 
            className="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            Sign in to continue
          </a>
        </div>
      </SignedOut>
    </div>
  );
} 