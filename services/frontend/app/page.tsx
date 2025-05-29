import { SignedIn, SignedOut } from "@clerk/nextjs";

export default function HomePage() {
  return (
    <div>
      <h1>Welcome to Briefly</h1>
      <SignedIn>
        <p>You are signed in. Explore your dashboard (to be built).</p>
        {/* Add more content for signed-in users here */}
      </SignedIn>
      <SignedOut>
        <p>Please sign in or sign up to continue.</p>
      </SignedOut>
    </div>
  );
} 