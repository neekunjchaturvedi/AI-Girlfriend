import React, { createContext, useContext, useState } from 'react';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);

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
        // If we already have user data, don't throw an error
        if (data.user) {
          setUser(data.user);
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
      localStorage.setItem('token', data.access_token);
      document.cookie = 'loggedIn=true; path=/';
      return data;
    } catch (error) {
      // Only throw error if we don't have user data
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

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
