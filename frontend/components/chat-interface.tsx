"use client"

import type React from "react"

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Bot, Loader2, Send, User } from "lucide-react"
import { useSession } from "next-auth/react"
import { useEffect, useRef, useState } from "react"

type Message = {
    id: number
    content: string
    sender: "user" | "ai"
    timestamp: Date
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
    const messagesEndRef = useRef<HTMLDivElement>(null)

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    const handleSendMessage = async () => {
        if (input.trim() && session?.user?.email) {
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
                // Send message to chat service via frontend API
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        message: currentInput,
                        user_email: session.user.email,
                    }),
                })

                if (!response.ok) {
                    throw new Error('Failed to send message')
                }

                const data = await response.json()

                // Add AI response
                const aiMessage: Message = {
                    id: messages.length + 2,
                    content: data.response || "I'm sorry, I couldn't process your request. Please try again.",
                    sender: "ai",
                    timestamp: new Date(),
                }
                setMessages((prev) => [...prev, aiMessage])
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
            <ScrollArea className="flex-1 p-4">
                <div className="space-y-4">
                    {messages.map((message) => (
                        <div key={message.id} className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"}`}>
                            <div className={`flex gap-3 max-w-[80%] ${message.sender === "user" ? "flex-row-reverse" : ""}`}>
                                <Avatar className="h-8 w-8">
                                    {message.sender === "ai" ? (
                                        <>
                                            {/* <AvatarImage src="/placeholder.svg?height=32&width=32" /> */}
                                            <AvatarImage className="bg-teal-100 text-teal-600">
                                                <Bot className="h-4 w-4" />
                                            </AvatarImage>
                                            <AvatarFallback className="bg-teal-100 text-teal-600">
                                                <Bot className="h-4 w-4" />
                                            </AvatarFallback>
                                        </>
                                    ) : (
                                        <>
                                            {/* <AvatarImage src="/placeholder.svg?height=32&width=32" /> */}
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
                                    className={`rounded-lg p-3 ${message.sender === "user" ? "bg-teal-600 text-white" : "bg-gray-100 text-gray-800"
                                        }`}
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
                    placeholder="Ask me anything about your schedule..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    className="flex-1"
                />
                <Button onClick={handleSendMessage} disabled={isLoading || !input.trim()}>
                    <Send className="h-4 w-4" />
                </Button>
            </div>
        </div>
    )
}
