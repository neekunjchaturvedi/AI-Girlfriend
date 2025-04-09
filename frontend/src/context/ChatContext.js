import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';
import axios from 'axios';

const ChatContext = createContext(null);

export const ChatProvider = ({ children }) => {
  const [chats, setChats] = useState([]);
  const [currentChat, setCurrentChat] = useState(null);
  const [loading, setLoading] = useState(false);
  const pollingInterval = useRef(null);

  const fetchChats = useCallback(async (silent = false) => {
    if (!silent) {
      setLoading(true);
    }
    
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        console.warn('No auth token found');
        return;
      }

      const response = await axios.get(`${process.env.REACT_APP_BACKEND_URL}/api/chats`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      const newChats = response.data.chats || [];
      if (JSON.stringify(newChats) !== JSON.stringify(chats)) {
        setChats(newChats);
      }
    } catch (error) {
      if (!silent) {
        console.error('Error fetching chats:', error);
      }
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }, [chats]);

  useEffect(() => {
    fetchChats(); // Initial fetch
    
    // Set up polling every 30 seconds
    pollingInterval.current = setInterval(() => {
      fetchChats(true); // Silent fetch for polling
    }, 30000);

    return () => {
      if (pollingInterval.current) {
        clearInterval(pollingInterval.current);
      }
    };
  }, [fetchChats]);

  const createNewChat = async (message) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('Authentication required');
      }

      const response = await axios.post(
        `${process.env.REACT_APP_BACKEND_URL}/api/chat/new`,
        { message },
        { 
          headers: { 
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.data || !response.data.chat_id) {
        throw new Error('Invalid response from server');
      }

      const newChat = {
        chat_id: response.data.chat_id,
        messages: response.data.messages || [],
        created_at: new Date().toISOString()
      };

      setChats(prev => [newChat, ...prev]);
      setCurrentChat(newChat);
      return newChat;

    } catch (error) {
      console.error('Error creating chat:', error?.response?.data || error.message);
      throw new Error(error?.response?.data?.detail || error.message);
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async (chatId, message) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${process.env.REACT_APP_BACKEND_URL}/api/chat/${chatId}/message`,
        { message },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      setChats(prev => prev.map(chat => {
        if (chat.chat_id === chatId) {
          return {
            ...chat,
            messages: [...chat.messages, ...response.data.messages]
          };
        }
        return chat;
      }));

      // Also update currentChat if this is the active chat
      if (currentChat?.chat_id === chatId) {
        setCurrentChat(prev => ({
          ...prev,
          messages: [...prev.messages, ...response.data.messages]
        }));
      }
      
      return response.data;
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const deleteChat = async (chatId) => {
    try {
      const token = localStorage.getItem('token');
      await axios.delete(
        `${process.env.REACT_APP_BACKEND_URL}/api/chat/${chatId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setChats(prev => prev.filter(chat => chat.chat_id !== chatId));
      if (currentChat?.chat_id === chatId) {
        setCurrentChat(null);
      }
    } catch (error) {
      console.error('Error deleting chat:', error);
      throw error;
    }
  };

  return (
    <ChatContext.Provider value={{
      chats,
      currentChat,
      loading,
      setCurrentChat,
      fetchChats,
      createNewChat,
      sendMessage,
      deleteChat
    }}>
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => useContext(ChatContext);
