import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '../context/ChatContext';
import MemoryPanel from './MemoryPanel';

const ChatInterface = () => {
  const [message, setMessage] = useState('');
  const { currentChat, loading, sendMessage } = useChat();
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [currentChat?.messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!message.trim() || !currentChat) return;

    try {
      await sendMessage(currentChat.chat_id, message.trim());
      setMessage('');
    } catch (error) {
      console.error('Error sending message:', error);
    }
  };

  const renderMessage = (msg, index) => (
    <div key={index} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
      <div
        className={`max-w-[70%] p-3 rounded-lg ${
          msg.role === 'user'
            ? 'bg-blue-600 text-white'
            : 'bg-gray-200 text-gray-800'
        }`}
      >
        {msg.text}
      </div>
      {msg.sentiment && (
        <span className="text-xs text-gray-500 mt-1">
          Mood: {msg.sentiment.dominant} ({Math.round(msg.sentiment.confidence * 100)}%)
        </span>
      )}
      {msg.role === 'user' && <MemoryPanel message={msg.text} />}
    </div>
  );

  if (!currentChat) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-gray-500 p-8">
        <h2 className="text-2xl font-semibold mb-4">Welcome to AI Chat</h2>
        <p className="text-center mb-8">
          Click the "Start Chat" button to begin a conversation with the Mistral AI assistant.
        </p>
        <div className="bg-gray-100 p-4 rounded-lg text-sm">
          <p>Features:</p>
          <ul className="list-disc pl-5 mt-2">
            <li>Smart AI responses</li>
            <li>Multiple chat sessions</li>
            <li>Message history</li>
          </ul>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {currentChat.messages.map((msg, index) => renderMessage(msg, index))}
        <div ref={messagesEndRef} />
      </div>
      
      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex gap-2">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Type your message..."
            className="flex-1 p-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !message.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-blue-300"
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              'Send'
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatInterface;
