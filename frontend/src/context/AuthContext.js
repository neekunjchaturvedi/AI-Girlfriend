import React, { createContext, useContext, useState } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [relationshipStage, setRelationshipStage] = useState('acquaintance');

  const login = async (code) => {
    setLoading(true);
    try {
      const redirectUri = encodeURIComponent(process.env.REACT_APP_REDIRECT_URI);
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/oauth2callback?code=${code}&redirect_uri=${redirectUri}`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        if (data.user) {
          setUser(data.user);
          setRelationshipStage(data.user.relationship_stage || 'acquaintance');
          localStorage.setItem('token', data.access_token);
          document.cookie = 'loggedIn=true; path=/';
          return data;
        }
        throw new Error(data.detail || 'Login failed');
      }
      
      if (!data.user || !data.access_token) {
        throw new Error('Invalid response data');
      }
      
      setUser(data.user);
      setRelationshipStage(data.user.relationship_stage || 'acquaintance');
      localStorage.setItem('token', data.access_token);
      document.cookie = 'loggedIn=true; path=/';
      return data;
    } catch (error) {
      if (!user) {
        throw error;
      }
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('token');
    document.cookie = 'loggedIn=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT';
  };

  const updateRelationshipStage = async (stage) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${process.env.REACT_APP_BACKEND_URL}/api/update-relationship`,
        { stage },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setRelationshipStage(stage);
    } catch (error) {
      console.error('Error updating relationship:', error);
      throw error;
    }
  };

  return (
    <AuthContext.Provider value={{ 
      user, 
      loading, 
      login, 
      logout,
      relationshipStage,
      updateRelationshipStage 
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
