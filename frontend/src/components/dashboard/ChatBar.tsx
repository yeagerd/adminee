'use client';

import React, { useState, KeyboardEvent } from 'react';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
}

const ChatBar: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');

  const handleSendMessage = () => {
    if (inputText.trim() === '') return;

    const newUserMessage: Message = {
      id: `msg-${Date.now()}`,
      text: inputText,
      sender: 'user',
    };

    setMessages(prevMessages => [...prevMessages, newUserMessage]);
    setInputText('');

    // Simulate a bot response for MVP frontend demonstration
    setTimeout(() => {
      const botResponse: Message = {
        id: `msg-${Date.now() + 1}`,
        text: `Echo: "${newUserMessage.text}" (This is a mock bot response)`, // Simple echo
        sender: 'bot',
      };
      setMessages(prevMessages => [...prevMessages, botResponse]);
    }, 500);
  };

  const handleKeyPress = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault(); // Prevent new line on enter
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-[300px] bg-white p-4 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-2">Chat with AI Assistant</h3>
      <div className="flex-grow overflow-y-auto mb-3 p-2 border rounded bg-gray-50">
        {messages.length === 0 && <p className="text-gray-400 italic text-center">No messages yet...</p>}
        {messages.map(msg => (
          <div key={msg.id} className={`mb-2 p-2 rounded-md max-w-[80%] ${msg.sender === 'user' ? 'bg-blue-500 text-white self-end ml-auto' : 'bg-gray-200 text-gray-800 self-start mr-auto'}`}>
            {msg.text}
          </div>
        ))}
      </div>
      <div className="flex">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message..."
          className="flex-grow p-2 border rounded-l focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleSendMessage}
          className="px-4 py-2 bg-blue-500 text-white rounded-r hover:bg-blue-600 focus:outline-none"
        >
          Send
        </button>
      </div>
    </div>
  );
};

export default ChatBar; 