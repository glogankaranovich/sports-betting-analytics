import React, { useState, useEffect } from 'react';
import { ModelList } from './ModelList';
import { ModelBuilder } from './ModelBuilder';
import { ModelDetail } from './ModelDetail';
import { CustomDataUpload } from './CustomDataUpload';
import { bettingApi } from '../services/api';

interface UserModelsProps {
  token: string;
  subscription?: any;
  onNavigate?: (page: string) => void;
}

export const UserModels: React.FC<UserModelsProps> = ({ token, subscription, onNavigate }) => {
  const [selectedModel, setSelectedModel] = useState<any>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showBuilderModal, setShowBuilderModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [userModels, setUserModels] = useState<any[]>([]);
  const [userId, setUserId] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Extract user ID from JWT token
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const extractedUserId = payload.sub || payload['cognito:username'];
        setUserId(extractedUserId);
      } catch (error) {
        console.error('Error parsing token:', error);
        setLoading(false);
      }
    }
  }, [token]);

  useEffect(() => {
    // Load models once we have both token and userId
    if (token && userId && subscription?.limits?.user_models) {
      loadUserModels();
    } else if (subscription) {
      setLoading(false);
    }
  }, [token, userId, subscription]);

  const loadUserModels = async () => {
    try {
      setLoading(true);
      const response = await bettingApi.getUserModels(token, userId);
      setUserModels(response.models || []);
    } catch (error: any) {
      console.error('Error loading user models:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateModel = async (config: any) => {
    try {
      await bettingApi.createUserModel(token, { ...config, user_id: userId });
      setShowBuilderModal(false);
      loadUserModels();
    } catch (error: any) {
      console.error('Error creating model:', error);
      const errorMessage = error.response?.data?.error || error.message || 'Failed to create model';
      
      // Show upgrade message for limit errors
      if (error.response?.status === 403) {
        alert(`⚠️ ${errorMessage}\n\nUpgrade your plan to create more models.`);
      } else {
        alert(errorMessage);
      }
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
    return <div className="loading">Loading...</div>;
  }

  // Step 1: Check if feature is enabled (from subscription limits which includes feature flags)
  const featureEnabled = subscription?.limits?.user_models === true;
  
  if (!featureEnabled) {
    return (
      <div style={{ textAlign: 'center', padding: '60px 20px' }}>
        <h2>User Models Coming Soon</h2>
        <p style={{ color: '#a0aec0', marginTop: '16px' }}>
          This feature is currently in beta testing and not yet available.
        </p>
      </div>
    );
  }

  // Step 2: Check if user has access via subscription tier
  const hasAccess = subscription?.limits?.max_user_models > 0;
  
  if (!hasAccess) {
    return (
      <div className="page-container">
        <div style={{ 
          padding: '40px', 
          textAlign: 'center',
          background: '#1a1a1a',
          borderRadius: '8px',
          border: '1px solid #333'
        }}>
          <h3 style={{ marginBottom: '16px' }}>🎯 Custom Models</h3>
          <p style={{ color: '#ccc', marginBottom: '24px' }}>
            Build and train your own prediction models with custom strategies.
          </p>
          <ul style={{ textAlign: 'left', color: '#ccc', marginBottom: '24px', listStyle: 'none', padding: 0 }}>
            <li style={{ padding: '8px 0', borderBottom: '1px solid #333' }}>✓ Create custom models</li>
            <li style={{ padding: '8px 0', borderBottom: '1px solid #333' }}>✓ Upload custom datasets</li>
            <li style={{ padding: '8px 0', borderBottom: '1px solid #333' }}>✓ Backtest strategies</li>
            <li style={{ padding: '8px 0' }}>✓ Track performance</li>
          </ul>
          <button 
            className="upgrade-btn" 
            onClick={() => onNavigate?.('subscription')}
            style={{ width: '100%' }}
          >
            Upgrade to Access Custom Models
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <h2 style={{ margin: 0 }}>My Models</h2>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button onClick={() => setShowUploadModal(true)} className="btn-secondary">
              Upload Custom Data
            </button>
            <button onClick={() => setShowBuilderModal(true)} className="btn-primary">
              Create New Model
            </button>
          </div>
        </div>
        <p style={{ margin: 0, color: '#a0aec0', fontSize: '14px' }}>
          {userModels.length}/3 models created (FREE tier)
          {userModels.length >= 3 && (
            <span style={{ color: '#f59e0b', marginLeft: '8px' }}>
              • Limit reached. Upgrade to create more.
            </span>
          )}
        </p>
      </div>
      <ModelList
        models={userModels}
        onView={(model) => {
          setSelectedModel(model);
          setShowDetailModal(true);
        }}
        onEdit={handleEditModel}
        onDelete={handleDeleteModel}
        onToggleStatus={handleToggleStatus}
      />
      {showDetailModal && selectedModel && (
        <ModelDetail
          model={selectedModel}
          token={token}
          onBack={() => {
            setShowDetailModal(false);
            setSelectedModel(null);
          }}
        />
      )}
      {showBuilderModal && (
        <ModelBuilder
          onSave={handleCreateModel}
          onCancel={() => setShowBuilderModal(false)}
        />
      )}
      {showUploadModal && (
        <CustomDataUpload
          token={token}
          userId={userId}
          onUploadComplete={() => setShowUploadModal(false)}
          onCancel={() => setShowUploadModal(false)}
        />
      )}
    </div>
  );
};
