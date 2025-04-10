import React from 'react';
import { useAuth } from '../context/AuthContext';

const stages = [
  { 
    id: 'acquaintance', 
    label: 'Acquaintance',
    activeClass: 'bg-blue-500 text-white',
    inactiveClass: 'bg-blue-50 text-blue-600 hover:bg-blue-100'
  },
  { 
    id: 'friend', 
    label: 'Friend',
    activeClass: 'bg-green-500 text-white',
    inactiveClass: 'bg-green-50 text-green-600 hover:bg-green-100'
  },
  { 
    id: 'girlfriend', 
    label: 'Girlfriend',
    activeClass: 'bg-pink-500 text-white',
    inactiveClass: 'bg-pink-50 text-pink-600 hover:bg-pink-100'
  }
];

const RelationshipStage = () => {
  const { relationshipStage, updateRelationshipStage } = useAuth();

  const handleStageChange = async (stage) => {
    try {
      await updateRelationshipStage(stage);
    } catch (error) {
      console.error('Failed to update relationship stage:', error);
    }
  };

  return (
    <div className="p-4 border-b bg-white">
      <h3 className="text-sm font-medium text-gray-700 mb-2">Relationship Stage</h3>
      <div className="flex gap-2 flex-wrap">
        {stages.map(({ id, label, activeClass, inactiveClass }) => (
          <button
            key={id}
            onClick={() => handleStageChange(id)}
            className={`
              px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 shadow-sm
              ${relationshipStage === id ? activeClass : inactiveClass}
              focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
            `}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
};

export default RelationshipStage;
