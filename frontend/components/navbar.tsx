import { Sailboat, Plus, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

export default function Navbar() {
  return (
    <header className="bg-white border-b">
      <div className="container mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sailboat className="h-6 w-6 text-teal-600" />
          <h1 className="text-xl font-semibold">Briefly</h1>
        </div>
        <div className="flex items-center gap-4">
          <Avatar>
            {/* <AvatarImage src="/placeholder.svg?height=40&width=40" alt="User" /> */}
            <AvatarImage className="bg-gray-100">
              <User className="h-4 w-4" />
            </AvatarImage>
            <AvatarFallback>JD</AvatarFallback>
          </Avatar>
        </div>
      </div>
    </header>
  );
}
