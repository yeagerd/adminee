import { Sailboat, Plus, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

import {
  ClerkProvider,
  SignInButton,
  SignUpButton,
  SignedIn,
  SignedOut,
  UserButton,
} from '@clerk/nextjs'

export default function Navbar() {
  return (
    <header className="bg-white border-b w-full">
      <div className="flex flex-row items-center justify-between w-full px-4 py-3 max-w-7xl mx-auto">
        <div className="flex items-center gap-2 min-w-0">
          <Sailboat className="h-6 w-6 text-teal-600 flex-shrink-0" />
          <h1 className="text-xl font-semibold truncate">Briefly</h1>
        </div>
        <div className="flex items-center gap-4 min-w-0">
            <SignedOut>
              <SignInButton />
              <SignUpButton />
            </SignedOut>
            <SignedIn>
              <UserButton />
            </SignedIn>
        </div>
      </div>
    </header>
  );
}
