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
    <header className="bg-white border-b">
      <div className="container mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sailboat className="h-6 w-6 text-teal-600" />
          <h1 className="text-xl font-semibold">Briefly</h1>
        </div>
        <div className="flex items-center gap-4">
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
