"use client"

import type React from "react"

import { Button } from "@/components/ui/button"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useStreamingSetting } from "@/hooks/use-streaming-setting"
import gatewayClient from "@/lib/gateway-client"
import { History, Loader2, Plus, Send } from "lucide-react"
import { useSession } from "next-auth/react"
import { useCallback, useEffect, useRef, useState } from "react"

type Message = {
    id: string
    content: string
    sender: "user" | "ai"
    timestamp: Date
}

// Draft type interfaces based on chat service Pydantic models
export interface DraftEmail {
    id?: string;
    type: "email"
    to?: string
    cc?: string
    bcc?: string
    subject?: string
    body?: string
    thread_id: string
    created_at: string
    updated_at?: string
}

export interface DraftCalendarEvent {
    id?: string;
    type: "calendar_event"
    title?: string
    start_time?: string
    end_time?: string
    attendees?: string
    location?: string
    description?: string
    thread_id: string
    created_at: string
    updated_at?: string
}

export interface DraftCalendarChange {
    id?: string;
    type: "calendar_change"
    event_id?: string
    change_type?: string
    new_title?: string
    new_start_time?: string
    new_end_time?: string
    new_attendees?: string
    new_location?: string
    new_description?: string
    thread_id: string
    created_at: string
    updated_at?: string
}

export type DraftData = DraftEmail | DraftCalendarEvent | DraftCalendarChange

interface ChatResponse {
    thread_id: string
    messages: Array<{
        message_id: string
        thread_id: string
        user_id: string
        llm_generated: boolean
        content: string
        created_at: string
    }>
    drafts?: DraftData[]
}

// Sample initial messages
const initialMessages: Message[] = []

function isUnbreakableString(str: string, threshold: number) {
    return typeof str === 'string' && str.length > threshold && !/\s/.test(str);
}

function ChatBubble({ content, sender, windowWidth }: { content: React.ReactNode, sender: "user" | "ai", windowWidth: number }) {
    if (typeof content !== 'string') return null;
    // Dynamic threshold scales with window width
    const threshold = Math.floor(windowWidth / 15);
    let breakClass = "";
    const words = content.split(/\s+/);
    if (words.some(word => isUnbreakableString(word, threshold))) {
        breakClass = "break-all";
    }
    console.log('Chat bubble word break threshold:', threshold, 'breakClass:', breakClass);
    return (
        <div
            className={`max-w-[95%] min-w-0 rounded-lg p-2 text-sm overflow-anywhere ${breakClass} ${sender === "user" ? "bg-teal-600 text-white ml-2" : "bg-gray-100 text-gray-800 mr-2"}`}
        >
            {content}
        </div>
    );
}

interface ChatInterfaceProps {
    containerRef?: React.RefObject<HTMLDivElement>;
    onDraftReceived?: (draft: DraftData) => void;
}

export default function ChatInterface({ containerRef, onDraftReceived }: ChatInterfaceProps) {
    const { data: session } = useSession()
    const [messages, setMessages] = useState<Message[]>(initialMessages)
    const [input, setInput] = useState("")
    const [isLoading, setIsLoading] = useState(false)
    const [chatHistory, setChatHistory] = useState<ThreadResponse[]>([])
    const [currentThreadId, setCurrentThreadId] = useState<string | null>(null)
    const { enableStreaming } = useStreamingSetting()
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const internalRef = useRef<HTMLDivElement>(null);
    const chatAreaRef = containerRef || internalRef;
    const [chatWidth, setChatWidth] = useState(600)
    const streamControllerRef = useRef<AbortController | null>(null)

    // Track chat window width
    useEffect(() => {
        function updateWidth() {
            if (chatAreaRef.current) {
                setChatWidth(chatAreaRef.current.offsetWidth)
            }
        }
        updateWidth();

        // Use ResizeObserver for the chat pane
        const observer = new window.ResizeObserver(() => {
            updateWidth();
        });
        if (chatAreaRef.current) {
            observer.observe(chatAreaRef.current);
        }
        return () => {
            observer.disconnect();
        };
    }, [chatAreaRef]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    // Use the correct ThreadResponse type for chat history
    interface ThreadResponse {
        thread_id: string;
        user_id: string;
        title?: string;
        created_at: string;
        updated_at: string;
    }

    const fetchChatHistory = useCallback(async () => {
        if (session) {
            try {
                // Use the correct ThreadResponse type and fallback for missing title
                const threads = (await gatewayClient.getChatThreads()) as ThreadResponse[]
                // Sort in reverse-chronological order (newest first)
                const sortedThreads = threads.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
                setChatHistory(sortedThreads)
            } catch (error) {
                console.error("Failed to fetch chat history:", error)
            }
        }
    }, [session])

    // Add state to track dropdown open
    const [historyDropdownOpen, setHistoryDropdownOpen] = useState(false);

    // Fetch chat history only when dropdown is opened and not already loaded
    const handleHistoryDropdownOpenChange = async (open: boolean) => {
        setHistoryDropdownOpen(open);
        if (open && chatHistory.length === 0) {
            await fetchChatHistory();
        }
    };

    const handleNewChat = () => {
        if (streamControllerRef.current) {
            streamControllerRef.current.abort()
        }
        setMessages(initialMessages)
        setCurrentThreadId(null)
    }

    const handleLoadChat = async (threadId: string) => {
        try {
            const history = (await gatewayClient.getChatHistory(threadId)) as ChatResponse
            const loadedMessages: Message[] = history.messages.map((msg) => ({
                id: msg.message_id,
                content: msg.content,
                sender: msg.llm_generated ? "ai" : "user",
                timestamp: new Date(msg.created_at),
            }))
            setMessages(loadedMessages)
            setCurrentThreadId(threadId)
        } catch (error) {
            console.error("Failed to load chat history:", error)
        }
    }

    const handleSendMessage = async () => {
        if (!session?.user?.email) {
            // Add message asking user to log in
            const loginMessage: Message = {
                id: self.crypto.randomUUID(),
                content: "Please log in to use the chat functionality. You can sign in using the button in the top right corner.",
                sender: "ai",
                timestamp: new Date(),
            }
            setMessages([...messages, loginMessage])
            return
        }

        if (input.trim()) {
            // Add user message
            const userMessage: Message = {
                id: self.crypto.randomUUID(),
                content: input.trim(),
                sender: "user",
                timestamp: new Date(),
            }
            setMessages([...messages, userMessage])
            const currentInput = input.trim()
            setInput("")
            setIsLoading(true)

            try {
                if (enableStreaming) {
                    streamControllerRef.current = new AbortController()
                    const stream = await gatewayClient.chatStream(currentInput, currentThreadId ?? undefined, undefined, streamControllerRef.current.signal)
                    const reader = stream.getReader()
                    const decoder = new TextDecoder()
                    const placeholderId = self.crypto.randomUUID()

                    // Add AI message placeholder
                    const aiMessage: Message = {
                        id: placeholderId,
                        content: "",
                        sender: "ai",
                        timestamp: new Date(),
                    }
                    setMessages((prev) => [...prev, aiMessage])

                    if (reader) {
                        const processStream = async () => {
                            let buffer = ""
                            let eventName: string | null = null
                            let serverMessageId: string | null = null
                            let streamedDraft: DraftData | null = null;
                            while (true) {
                                const { done, value } = await reader.read()
                                if (done) break

                                buffer += decoder.decode(value, { stream: true })
                                const lines = buffer.split("\n")
                                buffer = lines.pop() ?? ""

                                for (const line of lines) {
                                    if (line.startsWith("event:")) {
                                        eventName = line.substring(6).trim()
                                    } else if (line.startsWith("data:")) {
                                        const dataStr = line.substring(5).trim()
                                        if (eventName === "metadata") {
                                            try {
                                                const data = JSON.parse(dataStr)
                                                setCurrentThreadId(data.thread_id)
                                                serverMessageId = data.message_id
                                                if (data.drafts && data.drafts.length > 0) {
                                                    streamedDraft = data.drafts[0];
                                                }
                                            } catch (e) {
                                                console.error("Failed to parse metadata:", e)
                                            }
                                        } else if (eventName === "chunk") {
                                            try {
                                                const data = JSON.parse(dataStr)
                                                if (data.delta) {
                                                    setMessages((prev) => {
                                                        const newMessages = [...prev]
                                                        const lastMessage = newMessages[newMessages.length - 1]
                                                        if (lastMessage.sender === "ai") {
                                                            lastMessage.content += data.delta
                                                        }
                                                        return newMessages
                                                    })
                                                }
                                            } catch (e) {
                                                console.error("Failed to parse chunk:", e)
                                            }
                                        }
                                    } else if (line.trim() === "") {
                                        eventName = null // Reset on blank line
                                    }
                                }
                            }
                            if (serverMessageId) {
                                setMessages((prev) => prev.map(m => m.id === placeholderId ? { ...m, id: serverMessageId! } : m))
                            }
                            // Call onDraftReceived if a draft was streamed
                            if (streamedDraft && onDraftReceived) {
                                onDraftReceived(streamedDraft);
                            }
                        }
                        await processStream()
                    }
                } else {
                    // Non-streaming implementation using GatewayClient
                    const data = await gatewayClient.chat(currentInput, currentThreadId ?? undefined) as ChatResponse
                    if (!currentThreadId) {
                        fetchChatHistory()
                    }
                    setCurrentThreadId(data.thread_id)

                    // Extract the AI response from the backend response structure
                    const aiResponse = data.messages && data.messages.length > 0
                        ? data.messages[data.messages.length - 1].content
                        : "I'm sorry, I couldn't process your request. Please try again."

                    // Add AI response
                    const aiMessage: Message = {
                        id: data.messages && data.messages.length > 0 ? data.messages[data.messages.length - 1].message_id : `error-${self.crypto.randomUUID()}`,
                        content: aiResponse,
                        sender: "ai",
                        timestamp: new Date(),
                    }
                    setMessages((prev) => [...prev, aiMessage])

                    // If a draft is returned, pass it to the parent component
                    if (data.drafts && data.drafts.length > 0 && onDraftReceived) {
                        onDraftReceived(data.drafts[0]);
                    }
                }
            } catch (error) {
                console.error('Chat error:', error)
                // Add error message
                const errorMessage: Message = {
                    id: `error-${self.crypto.randomUUID()}`,
                    content: "I'm sorry, there was an error processing your request. Please try again.",
                    sender: "ai",
                    timestamp: new Date(),
                }
                setMessages((prev) => [...prev, errorMessage])
            } finally {
                setIsLoading(false)
                streamControllerRef.current = null
            }
        }
    }

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault()
            handleSendMessage()
        }
    }

    return (
        <div className="flex flex-col h-full relative" ref={chatAreaRef}>
            {/* Floating action buttons */}
            <div className="absolute top-4 right-4 z-10 flex gap-2">
                <Button variant="ghost" size="icon" onClick={handleNewChat} className="bg-black text-white hover:bg-gray-700 hover:text-white border border-gray-600">
                    <Plus className="h-5 w-5" />
                </Button>
                <DropdownMenu onOpenChange={handleHistoryDropdownOpenChange}>
                    <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="bg-black text-white hover:bg-gray-700 hover:text-white border border-gray-600">
                            <History className="h-5 w-5" />
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent className="max-h-96 overflow-y-auto">
                        {chatHistory.length === 0 ? (
                            <DropdownMenuItem disabled>
                                No chat history
                            </DropdownMenuItem>
                        ) : (
                            chatHistory.map((chat) => (
                                <DropdownMenuItem key={chat.thread_id} onClick={() => handleLoadChat(chat.thread_id)}>
                                    {/* Fallback for missing title */}
                                    {chat.title && chat.title.trim() !== '' ? chat.title : `Chat from ${new Date(chat.created_at).toLocaleString()}`}
                                </DropdownMenuItem>
                            ))
                        )}
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>

            <div className="flex-1 flex flex-col">
                <div className="flex-1 flex flex-col justify-end min-h-0">
                    <ScrollArea className="p-4">
                        <div className="flex flex-col space-y-4 w-full">
                            {messages.length === 0 ? (
                                <div className="flex items-center justify-center h-full min-h-[200px]">
                                    <div className="text-center text-gray-500">
                                        <div className="text-2xl font-semibold mb-2">What can I help you with?</div>
                                        <div className="text-sm">I can help you manage your schedule, draft emails, add tasks, and more.</div>
                                    </div>
                                </div>
                            ) : (
                                messages.map((message) => (
                                    <div
                                        key={message.id}
                                        className={`w-full flex ${message.sender === "user" ? "justify-end" : "justify-start"} min-w-0`}
                                    >
                                        <ChatBubble content={message.content} sender={message.sender} windowWidth={chatWidth} />
                                    </div>
                                ))
                            )}
                            {isLoading && (
                                <div className="w-full flex justify-start min-w-0">
                                    <ChatBubble content={<Loader2 className="h-5 w-5 animate-spin" />} sender="ai" windowWidth={chatWidth} />
                                </div>
                            )}
                            <div ref={messagesEndRef} />
                        </div>
                    </ScrollArea>
                </div>
            </div>
            <div className="p-4 border-t">
                <div className="flex gap-2">
                    <Input
                        placeholder="Type your message..."
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        className="flex-1"
                    />
                    <Button onClick={handleSendMessage} disabled={isLoading || !input.trim()}>
                        {isLoading ? <Loader2 className="h-4 w-4 mr-2" /> : <Send className="h-4 w-4" />}
                    </Button>
                </div>
            </div>
        </div>
    )
}