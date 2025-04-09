import React, { useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { useChat } from "../context/ChatContext";
import { useNavigate } from "react-router-dom";
import ChatList from "../components/ChatList";
import ChatInterface from "../components/ChatInterface";

const Dashboard = () => {
  const { user, logout } = useAuth();
  const { fetchChats } = useChat();
  const navigate = useNavigate();

  useEffect(() => {
    let mounted = true;
    
    const fetchData = async () => {
      if (mounted) {
        await fetchChats();
      }
    };

    fetchData();

    return () => {
      mounted = false;
    };
  }, []); // Empty dependency array since we only want to fetch once

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="h-16 bg-white shadow px-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <img
            src={user.picture}
            alt="Profile"
            className="w-8 h-8 rounded-full"
          />
          <div>
            <h1 className="font-semibold">{user.name}</h1>
            <p className="text-sm text-gray-600">{user.email}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
        >
          Logout
        </button>
      </div>

      <div className="h-[calc(100vh-4rem)] flex">
        <ChatList />
        <div className="flex-1">
          <ChatInterface />
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
