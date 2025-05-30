import { SignedIn, SignedOut } from "@clerk/nextjs";
import OnboardingStatus from "../components/OnboardingStatus"; // Adjusted path

export const dynamic = 'force-dynamic';

export default function HomePage() {
  return (
    <div>
      <h1>Welcome to Briefly</h1>
      <SignedIn>
        <p>You are signed in. This is your main dashboard (to be built).</p>
        <OnboardingStatus />
      </SignedIn>
      <SignedOut>
        <p>Please sign in or sign up to continue.</p>
      </SignedOut>
    </div>
  );
} 