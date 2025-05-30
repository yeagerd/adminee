import { PropsWithChildren } from 'react';
import Link from 'next/link';
import TimezoneSelector from '@/components/navigation/TimezoneSelector';
// We'll need Clerk's UserButton and auth utilities later
// import { UserButton, auth, currentUser } from '@clerk/nextjs';
// import { redirect } from 'next/navigation';
import '../globals.css'

export default async function MainAppLayout({ children }: PropsWithChildren) {
  // const { userId } = auth();
  // if (!userId) {
  //   redirect('/login'); // Or your Clerk sign-in path
  // }

  // const user = await currentUser(); // Optional: get user details for display

  return (
    <div className="flex min-h-screen flex-col">
      <header className="bg-gray-800 text-white p-4">
        <nav className="container mx-auto flex justify-between items-center">
          <Link href="/dashboard" className="text-xl font-bold">
            Briefly
          </Link>
          <div className="flex items-center space-x-4">
            <Link href="/dashboard" className="hover:text-gray-300">
              Dashboard
            </Link>
            <Link href="/settings" className="hover:text-gray-300">
              Settings
            </Link>
            <TimezoneSelector />
            {/* <UserButton afterSignOutUrl="/" /> */}
            {/* {user && <span>Hello, {user.firstName || user.emailAddresses[0]?.emailAddress}</span>} */}
          </div>
        </nav>
      </header>
      <main className="flex-grow container mx-auto p-4">
        {children}
      </main>
      <footer className="bg-gray-200 text-center p-4 text-sm">
        &copy; {new Date().getFullYear()} Briefly. All rights reserved.
      </footer>
    </div>
  );
} 