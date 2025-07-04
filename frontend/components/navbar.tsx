import { Sailboat } from "lucide-react";

export default function Navbar() {
  return (
    <header className="bg-white border-b w-full">
      <div className="flex flex-row items-center justify-between w-full px-4 py-3 max-w-7xl mx-auto">
        <div className="flex items-center gap-2 min-w-0">
          <Sailboat className="h-6 w-6 text-teal-600 flex-shrink-0" />
          <h1 className="text-xl font-semibold truncate">Briefly</h1>
        </div>
        <div className="flex items-center gap-4 min-w-0">
          {/* If you need NextAuth, add the provider or session logic here. For now, just render the navbar as usual. */}
        </div>
      </div>
    </header>
  );
}
