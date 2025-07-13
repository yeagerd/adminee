"use client"

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { demoChatMessages } from "@/lib/demo-data"
import { Bot, Send, User } from "lucide-react"
import { useState } from "react"

export function DemoChatInterface() {
    const [messages, setMessages] = useState(demoChatMessages)
    const [inputValue, setInputValue] = useState("")
    const [isTyping, setIsTyping] = useState(false)

    const handleSendMessage = async () => {
        if (!inputValue.trim()) return

        const userMessage = {
            id: Date.now().toString(),
            content: inputValue,
            isUser: true,
            timestamp: new Date()
        }

        setMessages(prev => [...prev, userMessage])
        setInputValue("")
        setIsTyping(true)

        // Simulate AI response delay
        setTimeout(() => {
            const aiResponses = [
                "I can help you with that! Let me check your calendar and find the relevant information.",
                "Based on your schedule, I can see you have some upcoming meetings. Would you like me to prepare a summary?",
                "I found some related documents in your Drive. Should I create a brief summary for your meeting?",
                "I can help you draft an email or prepare for your upcoming meetings. What would you like to focus on?",
                "Let me analyze your calendar and suggest some optimizations for your schedule."
            ]

            const randomResponse = aiResponses[Math.floor(Math.random() * aiResponses.length)]

            const aiMessage = {
                id: (Date.now() + 1).toString(),
                content: randomResponse,
                isUser: false,
                timestamp: new Date()
            }

            setMessages(prev => [...prev, aiMessage])
            setIsTyping(false)
        }, 1500)
    }

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSendMessage()
        }
    }

    return (
        <div className="flex flex-col h-[400px]">
            {/* Messages Area */}
            <ScrollArea className="flex-1 p-4 border rounded-lg bg-gray-50">
                <div className="space-y-4">
                    {messages.map((message) => (
                        <div
                            key={message.id}
                            className={`flex gap-3 ${message.isUser ? 'justify-end' : 'justify-start'}`}
                        >
                            {!message.isUser && (
                                <Avatar className="h-8 w-8">
                                    <AvatarImage src="/placeholder-user.jpg" />
                                    <AvatarFallback className="bg-teal-100 text-teal-600">
                                        <Bot className="h-4 w-4" />
                                    </AvatarFallback>
                                </Avatar>
                            )}

                            <div
                                className={`max-w-[80%] rounded-lg px-3 py-2 ${message.isUser
                                        ? 'bg-teal-600 text-white'
                                        : 'bg-white border text-gray-900'
                                    }`}
                            >
                                <p className="text-sm">{message.content}</p>
                                <p className={`text-xs mt-1 ${message.isUser ? 'text-teal-100' : 'text-gray-500'
                                    }`}>
                                    {message.timestamp.toLocaleTimeString([], {
                                        hour: '2-digit',
                                        minute: '2-digit'
                                    })}
                                </p>
                            </div>

                            {message.isUser && (
                                <Avatar className="h-8 w-8">
                                    <AvatarImage src="/placeholder-user.jpg" />
                                    <AvatarFallback className="bg-gray-100 text-gray-600">
                                        <User className="h-4 w-4" />
                                    </AvatarFallback>
                                </Avatar>
                            )}
                        </div>
                    ))}

                    {isTyping && (
                        <div className="flex gap-3 justify-start">
                            <Avatar className="h-8 w-8">
                                <AvatarImage src="/placeholder-user.jpg" />
                                <AvatarFallback className="bg-teal-100 text-teal-600">
                                    <Bot className="h-4 w-4" />
                                </AvatarFallback>
                            </Avatar>
                            <div className="bg-white border rounded-lg px-3 py-2">
                                <div className="flex space-x-1">
                                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </ScrollArea>

            {/* Input Area */}
            <div className="flex gap-2 mt-4">
                <Input
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Ask me anything about your schedule, tasks, or emails..."
                    className="flex-1"
                    disabled={isTyping}
                />
                <Button
                    onClick={handleSendMessage}
                    disabled={!inputValue.trim() || isTyping}
                    size="icon"
                >
                    <Send className="h-4 w-4" />
                </Button>
            </div>

            {/* Demo Notice */}
            <div className="mt-3 text-center">
                <p className="text-xs text-gray-500">
                    💡 This is a demo chat interface. In the real app, I can help you with calendar management,
                    email drafting, and task organization.
                </p>
            </div>
        </div>
    )
} 