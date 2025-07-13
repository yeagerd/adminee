"use client"

import type React from "react"

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import gatewayClient from "@/lib/gateway-client"
import { Bot, Loader2, Send, User } from "lucide-react"
import { useSession } from "next-auth/react"
import { useEffect, useRef, useState } from "react"

type Message = {
    id: number
    content: string
    sender: "user" | "ai"
    timestamp: Date
}

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
    drafts?: Array<{
        type: string
        [key: string]: any
    }>
}

// Sample initial messages
const initialMessages: Message[] = [
    {
        id: 1,
        content:
            "Hello! I'm your calendar assistant. I can help you manage your schedule, draft emails, add tasks, and more. How can I help you today?",
        sender: "ai",
        timestamp: new Date(),
    },
]

export default function ChatInterface() {
    const { data: session } = useSession()
    const [messages, setMessages] = useState<Message[]>(initialMessages)
    const [input, setInput] = useState("")
    const [isLoading, setIsLoading] = useState(false)
    const [enableStreaming, setEnableStreaming] = useState(false)
    const messagesEndRef = useRef<HTMLDivElement>(null)

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    const handleSendMessage = async () => {
        if (!session?.user?.email) {
            // Add message asking user to log in
            const loginMessage: Message = {
                id: messages.length + 1,
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
                id: messages.length + 1,
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
                    // Streaming implementation using GatewayClient
                    const stream = await gatewayClient.chatStream(currentInput)
                    const reader = stream.getReader()
                    const decoder = new TextDecoder()

                    // Add AI message placeholder
                    const aiMessage: Message = {
                        id: messages.length + 2,
                        content: "",
                        sender: "ai",
                        timestamp: new Date(),
                    }
                    setMessages((prev) => [...prev, aiMessage])

                    if (reader) {
                        while (true) {
                            const { done, value } = await reader.read()
                            if (done) break

                            const chunk = decoder.decode(value)
                            setMessages((prev) => {
                                const newMessages = [...prev]
                                const lastMessage = newMessages[newMessages.length - 1]
                                if (lastMessage.sender === "ai") {
                                    lastMessage.content += chunk
                                }
                                return newMessages
                            })
                        }
                    }
                } else {
                    // Non-streaming implementation using GatewayClient
                    const data = await gatewayClient.chat(currentInput) as ChatResponse

                    // Extract the AI response from the backend response structure
                    const aiResponse = data.messages && data.messages.length > 0
                        ? data.messages[data.messages.length - 1].content
                        : "I'm sorry, I couldn't process your request. Please try again."

                    // Add AI response
                    const aiMessage: Message = {
                        id: messages.length + 2,
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
                    id: messages.length + 2,
                    content: "I'm sorry, there was an error processing your request. Please try again.",
                    sender: "ai",
                    timestamp: new Date(),
                }
                setMessages((prev) => [...prev, errorMessage])
            } finally {
                setIsLoading(false)
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
        <div className="flex flex-col h-[300px]">
            {/* Development streaming toggle process.env.NODE_ENV === 'development' && {(*/}

            <div className="flex items-center space-x-2 p-2 bg-gray-50 border-b">
                <Checkbox
                    id="streaming"
                    checked={enableStreaming}
                    onCheckedChange={(checked) => setEnableStreaming(checked as boolean)}
                />
                <label htmlFor="streaming" className="text-sm text-gray-600">
                    Enable streaming (dev only)
                </label>
            </div>


            <ScrollArea className="flex-1 p-4">
                <div className="space-y-4">
                    {messages.map((message) => (
                        <div key={message.id} className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"}`}>
                            <div className={`flex gap-3 max-w-[80%] ${message.sender === "user" ? "flex-row-reverse" : ""}`}>
                                <Avatar className="h-8 w-8">
                                    {message.sender === "ai" ? (
                                        <>
                                            <AvatarImage className="bg-teal-100 text-teal-600">
                                                <Bot className="h-4 w-4" />
                                            </AvatarImage>
                                            <AvatarFallback className="bg-teal-100 text-teal-600">
                                                <Bot className="h-4 w-4" />
                                            </AvatarFallback>
                                        </>
                                    ) : (
                                        <>
                                            <AvatarImage className="bg-gray-100">
                                                <User className="h-4 w-4" />
                                            </AvatarImage>
                                            <AvatarFallback className="bg-gray-100">
                                                <User className="h-4 w-4" />
                                            </AvatarFallback>
                                        </>
                                    )}
                                </Avatar>
                                <div
                                    className={`rounded-lg p-3 ${message.sender === "user" ? "bg-teal-600 text-white" : "bg-gray-100 text-gray-800"}`}
                                >
                                    <p>{message.content}</p>
                                    <p className="text-xs opacity-70 mt-1">
                                        {message.timestamp.toLocaleTimeString([], {
                                            hour: "2-digit",
                                            minute: "2-digit",
                                        })}
                                    </p>
                                </div>
                            </div>
                        </div>
                    ))}
                    {isLoading && (
                        <div className="flex justify-start">
                            <div className="flex gap-3 max-w-[80%]">
                                <Avatar className="h-8 w-8">
                                    <AvatarFallback className="bg-teal-100 text-teal-600">
                                        <Bot className="h-4 w-4" />
                                    </AvatarFallback>
                                </Avatar>
                                <div className="rounded-lg p-3 bg-gray-100 text-gray-800">
                                    <Loader2 className="h-5 w-5 animate-spin" />
                                </div>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>
            </ScrollArea>

            <div className="p-3 border-t flex gap-2">
                <Input
                    placeholder={session?.user?.email ? "Ask me anything about your schedule..." : "Please log in to chat..."}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    className="flex-1"
                    disabled={!session?.user?.email}
                />
                <Button
                    onClick={handleSendMessage}
                    disabled={isLoading || !input.trim() || !session?.user?.email}
                    title={!session?.user?.email ? "Please log in to use chat" : ""}
                >
                    <Send className="h-4 w-4" />
                </Button>
            </div>
        </div>
    )
}
