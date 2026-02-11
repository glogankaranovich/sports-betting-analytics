import React, { useState } from 'react';
import './CustomDataUpload.css';

interface CustomDataUploadProps {
  token: string;
  userId: string;
  onUploadComplete: () => void;
  onCancel: () => void;
}

export const CustomDataUpload: React.FC<CustomDataUploadProps> = ({ token, userId, onUploadComplete, onCancel }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [sport, setSport] = useState('basketball_nba');
  const [dataType, setDataType] = useState('team');
  const [fileContent, setFileContent] = useState('');
  const [fileFormat, setFileFormat] = useState('csv');
  const [allowBennyAccess, setAllowBennyAccess] = useState(false);
  const [preview, setPreview] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      setFileContent(content);

      // Parse for preview
      if (file.name.endsWith('.csv')) {
        setFileFormat('csv');
        const lines = content.split('\n').filter(l => l.trim());
        const headers = lines[0].split(',');
        const previewData = lines.slice(1, 6).map(line => {
          const values = line.split(',');
          const row: any = {};
          headers.forEach((h, i) => row[h.trim()] = values[i]?.trim());
          return row;
        });
        setPreview(previewData);
      } else {
        setFileFormat('json');
        try {
          const data = JSON.parse(content);
          setPreview(data.slice(0, 5));
        } catch (err) {
          setError('Invalid JSON format');
        }
      }
    };
    reader.readAsText(file);
  };

  const handleUpload = async () => {
    if (!name || !fileContent) {
      setError('Name and file are required');
      return;
    }

    setUploading(true);
    setError('');

    try {
      const response = await fetch('/api/custom-data/upload', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          user_id: userId,
          name,
          description,
          sport,
          data_type: dataType,
          data: fileContent,
          format: fileFormat,
          allow_benny_access: allowBennyAccess,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Upload failed');
      }

      onUploadComplete();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button onClick={onCancel} className="close-button">×</button>
        <h2>Upload Custom Dataset</h2>
        
        <div className="info-box">
          <strong>📊 How it works:</strong>
          <p>Upload your own data to enhance predictions. Your data will be compared against game matchups.</p>
          <details>
            <summary>View example formats</summary>
            <div className="example">
              <strong>Team Data (CSV):</strong>
              <pre>{`team,power_rating,offensive_rating,defensive_rating
Los Angeles Lakers,85.5,112.3,108.1
Boston Celtics,88.2,115.7,106.4`}</pre>
              
              <strong>Player Data (JSON):</strong>
              <pre>{`[
  {"player": "LeBron James", "avg_points": 28.5, "recent_form": 32.1},
  {"player": "Stephen Curry", "avg_points": 29.8, "recent_form": 27.3}
]`}</pre>
            </div>
          </details>
        </div>

        <div className="form-group">
          <label>Dataset Name *</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Team Power Rankings"
            maxLength={50}
          />
        </div>

        <div className="form-group">
          <label>Description</label>
          <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Brief description of the dataset"
          maxLength={200}
        />
      </div>

      <div className="form-group">
        <label>Sport *</label>
        <select value={sport} onChange={(e) => setSport(e.target.value)}>
          <option value="basketball_nba">Basketball (NBA)</option>
          <option value="americanfootball_nfl">Football (NFL)</option>
          <option value="baseball_mlb">Baseball (MLB)</option>
          <option value="icehockey_nhl">Hockey (NHL)</option>
          <option value="soccer_epl">Soccer (EPL)</option>
        </select>
      </div>

      <div className="form-group">
        <label>Data Type *</label>
        <select value={dataType} onChange={(e) => setDataType(e.target.value)}>
          <option value="team">Team Data</option>
          <option value="player">Player Data</option>
        </select>
        <p className="help-text">
          {dataType === 'team' ? 'Must include "team" column' : 'Must include "player" column'}
        </p>
      </div>

      <div className="form-group">
        <label>Upload File (CSV or JSON) *</label>
        <input
          type="file"
          accept=".csv,.json"
          onChange={handleFileUpload}
        />
        <p className="help-text">Max 10,000 rows. All rows must have the same columns.</p>
      </div>

      {preview.length > 0 && (
        <div className="preview">
          <h3>Preview (first 5 rows)</h3>
          <div className="preview-table">
            <table>
              <thead>
                <tr>
                  {Object.keys(preview[0]).map(key => (
                    <th key={key}>{key}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.map((row, i) => (
                  <tr key={i}>
                    {Object.values(row).map((val: any, j) => (
                      <td key={j}>{val}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="form-group">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={allowBennyAccess}
            onChange={(e) => setAllowBennyAccess(e.target.checked)}
          />
          <div>
            <strong>Allow Benny to use this dataset</strong>
            <p className="help-text">
              If enabled, Benny can access this dataset when making predictions.
            </p>
          </div>
        </label>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="button-group">
        <button onClick={onCancel} className="btn-secondary" disabled={uploading}>
          Cancel
        </button>
        <button onClick={handleUpload} className="btn-primary" disabled={uploading || !name || !fileContent}>
          {uploading ? 'Uploading...' : 'Upload Dataset'}
        </button>
      </div>
      </div>
    </div>
  );
};
