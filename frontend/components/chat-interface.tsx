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
import { useEffect, useRef, useState } from "react"

type Message = {
    id: string
    content: string
    sender: "user" | "ai"
    timestamp: Date
}

// Draft type interfaces based on chat service Pydantic models
interface DraftEmail {
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

interface DraftCalendarEvent {
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

interface DraftCalendarChange {
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

type DraftData = DraftEmail | DraftCalendarEvent | DraftCalendarChange

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
const initialMessages: Message[] = [
    {
        id: "1",
        content:
            "Hello! I'm your calendar assistant. I can help you manage your schedule, draft emails, add tasks, and more. How can I help you today?",
        sender: "ai",
        timestamp: new Date(),
    },
]

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
}

export default function ChatInterface({ containerRef }: ChatInterfaceProps) {
    const { data: session } = useSession()
    const [messages, setMessages] = useState<Message[]>(initialMessages)
    const [input, setInput] = useState("")
    const [isLoading, setIsLoading] = useState(false)
    const [chatHistory, setChatHistory] = useState<{ thread_id: string; title: string; created_at: string }[]>([])
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

    const fetchChatHistory = async () => {
        if (session) {
            try {
                const threads = (await gatewayClient.getChatThreads()) as { thread_id: string; title: string; created_at: string }[]
                setChatHistory(threads)
            } catch (error) {
                console.error("Failed to fetch chat history:", error)
            }
        }
    }

    useEffect(() => {
        fetchChatHistory()
    }, [session])

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
                    const stream = await gatewayClient.chatStream(currentInput, currentThreadId ?? undefined)
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
        <div className="flex flex-col h-full" ref={chatAreaRef}>
            <div className="flex items-center justify-between p-4 border-b">
                <h2 className="text-lg font-semibold">Chat</h2>
                <div className="flex gap-2">
                    <Button variant="ghost" size="icon" onClick={handleNewChat}>
                        <Plus className="h-5 w-5" />
                    </Button>
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                                <History className="h-5 w-5" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent>
                            {chatHistory.map((chat) => (
                                <DropdownMenuItem key={chat.thread_id} onClick={() => handleLoadChat(chat.thread_id)}>
                                    {chat.title || `Chat from ${new Date(chat.created_at).toLocaleString()}`}
                                </DropdownMenuItem>
                            ))}
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            </div>
            <ScrollArea className="flex-1 p-4">
                <div className="flex flex-col space-y-4 w-full">
                    {messages.map((message) => (
                        <div
                            key={message.id}
                            className={`w-full flex ${message.sender === "user" ? "justify-end" : "justify-start"} min-w-0`}
                        >
                            <ChatBubble content={message.content} sender={message.sender} windowWidth={chatWidth} />
                        </div>
                    ))}
                    {isLoading && (
                        <div className="w-full flex justify-start min-w-0">
                            <ChatBubble content={<Loader2 className="h-5 w-5 animate-spin" />} sender="ai" windowWidth={chatWidth} />
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>
            </ScrollArea>
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