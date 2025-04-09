import React, { useEffect, useCallback, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import LoginButton from '../components/LoginButton';

const LoginPage = () => {
  const { login, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [isProcessing, setIsProcessing] = useState(false);

  const handleCode = useCallback(async (code) => {
    if (isProcessing) return; // Prevent multiple requests
    
    try {
      setIsProcessing(true);
      await login(code);
      // Clear the URL parameters after successful login
      window.history.replaceState({}, document.title, '/');
      navigate('/dashboard', { replace: true });
    } catch (error) {
      console.error('Login failed:', error);
      if (error.message.includes('expired or already been used')) {
        window.history.replaceState({}, document.title, '/');
        navigate('/', { replace: true });
      }
      // Don't show alert for successful logins that have secondary failures
      if (!document.cookie.includes('loggedIn')) {
        alert(error.message || 'Authentication failed. Please try again.');
      }
    } finally {
      setIsProcessing(false);
    }
  }, [login, navigate, isProcessing]);

  useEffect(() => {
    const urlParams = new URLSearchParams(location.search);
    const code = urlParams.get('code');
    const error = urlParams.get('error');
    
    if (error) {
      console.error('OAuth error:', error);
      alert('Authentication failed: ' + error);
      return;
    }
    
    if (code) {
      handleCode(code);
    }
  }, [location, handleCode]);

  const handleLogin = async () => {
    try {
      const redirectUri = encodeURIComponent(process.env.REACT_APP_REDIRECT_URI);
      const scope = encodeURIComponent('openid profile email');
      window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${process.env.REACT_APP_GOOGLE_CLIENT_ID}&response_type=code&scope=${scope}&redirect_uri=${redirectUri}&access_type=offline&prompt=consent`;
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-md">
        <h1 className="text-2xl font-bold mb-6 text-center">Welcome</h1>
        <LoginButton onClick={handleLogin} isLoading={loading} />
      </div>
    </div>
  );
};

export default LoginPage;
