import UserMenu from "@/components/auth/user-menu";
import { Button } from "@/components/ui/button";
import { useChatPanelState } from "@/contexts/chat-panel-context";
import { MessageSquare, MessageSquareOff, Sailboat, Settings } from "lucide-react";
import Link from "next/link";

export default function Navbar() {
    const { isOpen, toggle } = useChatPanelState();

    return (
        <header className="bg-white border-b w-full">
            <div className="flex flex-row items-center justify-between w-full px-4 py-3">
                <div className="flex items-center gap-2 min-w-0">
                    <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                        <Sailboat className="h-6 w-6 text-teal-600 flex-shrink-0" />
                        <h1 className="text-xl font-semibold truncate">Briefly</h1>
                    </Link>
                </div>
                <div className="flex items-center gap-4 min-w-0">
                    <Button
                        variant={isOpen ? "default" : "outline"}
                        size="sm"
                        onClick={toggle}
                        className={isOpen ? "bg-teal-600 hover:bg-teal-700" : ""}
                        title={isOpen ? "Close chat" : "Open chat"}
                    >
                        {isOpen ? (
                            <MessageSquare className="h-4 w-4" />
                        ) : (
                            <MessageSquareOff className="h-4 w-4" />
                        )}
                    </Button>
                    <Button variant="outline" size="sm" asChild>
                        <Link href="/settings">
                            <Settings className="h-4 w-4" />
                        </Link>
                    </Button>
                    <UserMenu />
                </div>
            </div>
        </header>
    );
}
