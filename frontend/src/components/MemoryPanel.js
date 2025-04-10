import React, { useState, useEffect } from 'react';
import axios from 'axios';

const MemoryPanel = ({ message }) => {
  const [memories, setMemories] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchMemories = async () => {
      if (!message) return;
      
      setLoading(true);
      try {
        const token = localStorage.getItem('token');
        const response = await axios.get(
          `${process.env.REACT_APP_BACKEND_URL}/api/memories?query=${encodeURIComponent(message)}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setMemories(response.data.memories);
      } catch (error) {
        console.error('Error fetching memories:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchMemories();
  }, [message]);

  if (loading || memories.length === 0) return null;

  return (
    <div className="mt-2 p-2 bg-gray-50 rounded-lg text-sm">
      <h4 className="font-medium text-gray-700 mb-1">Related Memories:</h4>
      <ul className="space-y-1">
        {memories.map((memory, index) => (
          <li key={index} className="text-gray-600">• {memory}</li>
        ))}
      </ul>
    </div>
  );
};

export default MemoryPanel;
