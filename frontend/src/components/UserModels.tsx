import React, { useState, useEffect } from 'react';
import { ModelList } from './ModelList';
import { ModelBuilder } from './ModelBuilder';
import { ModelDetail } from './ModelDetail';
import { bettingApi } from '../services/api';

interface UserModelsProps {
  token: string;
}

export const UserModels: React.FC<UserModelsProps> = ({ token }) => {
  const [showBuilder, setShowBuilder] = useState(false);
  const [selectedModel, setSelectedModel] = useState<any>(null);
  const [userModels, setUserModels] = useState<any[]>([]);
  const [userId] = useState('test_user'); // TODO: Get from Cognito user context
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      loadUserModels();
    }
  }, [token]);

  const loadUserModels = async () => {
    try {
      setLoading(true);
      const response = await bettingApi.getUserModels(token, userId);
      setUserModels(response.models || []);
    } catch (error) {
      console.error('Error loading user models:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateModel = async (config: any) => {
    try {
      await bettingApi.createUserModel(token, { ...config, user_id: userId });
      setShowBuilder(false);
      loadUserModels();
    } catch (error) {
      console.error('Error creating model:', error);
      alert('Failed to create model. Please try again.');
    }
  };

  const handleDeleteModel = async (modelId: string) => {
    if (!window.confirm('Are you sure you want to delete this model?')) return;
    
    try {
      await bettingApi.deleteUserModel(token, modelId, userId);
      loadUserModels();
    } catch (error) {
      console.error('Error deleting model:', error);
      alert('Failed to delete model. Please try again.');
    }
  };

  const handleToggleStatus = async (modelId: string, currentStatus: string) => {
    try {
      const newStatus = currentStatus === 'active' ? 'inactive' : 'active';
      await bettingApi.updateUserModel(token, modelId, { user_id: userId, status: newStatus });
      loadUserModels();
    } catch (error) {
      console.error('Error updating model status:', error);
      alert('Failed to update model status. Please try again.');
    }
  };

  const handleEditModel = (modelId: string) => {
    alert('Edit functionality coming soon!');
  };

  if (loading) {
    return <div className="loading">Loading your models...</div>;
  }

  if (selectedModel) {
    return (
      <ModelDetail
        model={selectedModel}
        token={token}
        onBack={() => setSelectedModel(null)}
      />
    );
  }

  if (showBuilder) {
    return (
      <ModelBuilder
        onSave={handleCreateModel}
        onCancel={() => setShowBuilder(false)}
      />
    );
  }

  return (
    <ModelList
      models={userModels}
      onCreateNew={() => setShowBuilder(true)}
      onView={(model) => setSelectedModel(model)}
      onEdit={handleEditModel}
      onDelete={handleDeleteModel}
      onToggleStatus={handleToggleStatus}
    />
  );
};
