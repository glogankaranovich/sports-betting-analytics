import React, { useState, useEffect } from 'react';
import { ModelList } from './ModelList';
import { ModelBuilder } from './ModelBuilder';
import { ModelDetail } from './ModelDetail';
import { CustomDataUpload } from './CustomDataUpload';
import { bettingApi } from '../services/api';

interface UserModelsProps {
  token: string;
}

export const UserModels: React.FC<UserModelsProps> = ({ token }) => {
  const [view, setView] = useState<'list' | 'builder' | 'detail' | 'upload'>('list');
  const [selectedModel, setSelectedModel] = useState<any>(null);
  const [userModels, setUserModels] = useState<any[]>([]);
  const [userId, setUserId] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Extract user ID from JWT token
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        setUserId(payload.sub || payload['cognito:username']);
      } catch (error) {
        console.error('Error parsing token:', error);
      }
    }
  }, [token]);

  useEffect(() => {
    if (token && userId) {
      loadUserModels();
    }
  }, [token, userId]);

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
      setView('list');
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

  if (view === 'detail' && selectedModel) {
    return (
      <ModelDetail
        model={selectedModel}
        token={token}
        onBack={() => {
          setSelectedModel(null);
          setView('list');
        }}
      />
    );
  }

  if (view === 'builder') {
    return (
      <ModelBuilder
        onSave={handleCreateModel}
        onCancel={() => setView('list')}
      />
    );
  }

  if (view === 'upload') {
    return (
      <CustomDataUpload
        token={token}
        userId={userId}
        onUploadComplete={() => setView('list')}
        onCancel={() => setView('list')}
      />
    );
  }

  return (
    <div>
      <div style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>My Models</h2>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button onClick={() => setView('upload')} className="btn-secondary">
            Upload Custom Data
          </button>
          <button onClick={() => setView('builder')} className="btn-primary">
            Create New Model
          </button>
        </div>
      </div>
      <ModelList
        models={userModels}
        onView={(model) => {
          setSelectedModel(model);
          setView('detail');
        }}
        onEdit={handleEditModel}
        onDelete={handleDeleteModel}
        onToggleStatus={handleToggleStatus}
      />
    </div>
  );
};
