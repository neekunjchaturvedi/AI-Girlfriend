import React from 'react';
import { useChat } from '../context/ChatContext';

const ChatList = () => {
  const { chats, currentChat, setCurrentChat, createNewChat, deleteChat, loading } = useChat();

  const handleNewChat = async () => {
    if (loading) return;
    
    try {
      // Remove the initial message and let it be created only when user sends their first message
      const result = await createNewChat();
      if (!result?.chat_id) {
        throw new Error('Invalid chat response');
      }
    } catch (error) {
      console.error('Error creating chat:', error);
      alert('Failed to create chat. Please try again.');
    }
  };

  return (
    <div className="w-64 border-r h-full flex flex-col">
      <div className="p-4 border-b">
        {chats.length === 0 ? (
          <button
            onClick={handleNewChat}
            disabled={loading}
            className="w-full px-4 py-4 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:bg-green-300 text-lg font-semibold"
          >
            {loading ? (
              <div className="w-6 h-6 border-3 border-white border-t-transparent rounded-full animate-spin mx-auto" />
            ) : (
              'Start Chat'
            )}
          </button>
        ) : (
          <button
            onClick={handleNewChat}
            disabled={loading}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-blue-300 disabled:cursor-not-allowed"
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mx-auto" />
            ) : (
              'New Chat'
            )}
          </button>
        )}
      </div>
      
      <div className="flex-1 overflow-y-auto">
        {chats.map((chat) => (
          <div
            key={chat.chat_id}
            className={`p-4 cursor-pointer hover:bg-gray-100 flex justify-between items-center ${
              currentChat?.chat_id === chat.chat_id ? 'bg-gray-100' : ''
            }`}
            onClick={() => setCurrentChat(chat)}
          >
            <div className="truncate flex-1">
              {chat.messages[0]?.text || 'New Chat'}
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                deleteChat(chat.chat_id);
              }}
              className="ml-2 text-red-500 hover:text-red-700"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ChatList;
