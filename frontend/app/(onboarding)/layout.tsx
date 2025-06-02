import { PropsWithChildren } from 'react';

export default function OnboardingLayout({ children }: PropsWithChildren) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-100 p-4">
      <div className="w-full max-w-md bg-white p-8 rounded-lg shadow-md">
        {/* You could add a logo or a specific onboarding header here if needed */}
        {children}
      </div>
      <footer className="mt-8 text-center text-sm text-gray-500">
        &copy; {new Date().getFullYear()} Briefly. Welcome!
      </footer>
    </div>
  );
} 