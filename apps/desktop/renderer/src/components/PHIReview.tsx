import React, { useState, useEffect } from 'react';
import { Eye, EyeOff, Check, X, RefreshCw, Save, AlertTriangle } from 'lucide-react';

interface Entity {
  id: string;
  label: string;
  text: string;
  start: number;
  end: number;
  confidence: number;
  method: string;
  contexts?: Array<{
    chunk_id: string;
    context: string;
    channel: string;
    t0: number;
    t1: number;
  }>;
}

interface Snapshot {
  snapshot_id: string;
  entities: Entity[];
  preview_diff: string;
  original_length: number;
  redacted_length: number;
  redacted_text: string;
}

const PHIReview: React.FC = () => {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [entityStatuses, setEntityStatuses] = useState<Record<string, boolean>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [previewMode, setPreviewMode] = useState<'diff' | 'redacted' | 'original'>('diff');
  const [filterLabel, setFilterLabel] = useState<string>('ALL');
  const [isApplying, setIsApplying] = useState(false);

  useEffect(() => {
    loadSnapshot();
  }, []);

  const loadSnapshot = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:7032/redaction/snapshot');
      const snapshotData = await response.json();
      
      setSnapshot(snapshotData);
      
      // Initialize all entities as accepted by default
      const statuses: Record<string, boolean> = {};
      snapshotData.entities.forEach((entity: Entity) => {
        statuses[entity.id] = true;
      });
      setEntityStatuses(statuses);
      
    } catch (error) {
      console.error('Error loading snapshot:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleEntity = (entityId: string) => {
    setEntityStatuses(prev => ({
      ...prev,
      [entityId]: !prev[entityId]
    }));
  };

  const toggleAllEntities = (accepted: boolean) => {
    const newStatuses: Record<string, boolean> = {};
    if (snapshot) {
      snapshot.entities.forEach(entity => {
        newStatuses[entity.id] = accepted;
      });
    }
    setEntityStatuses(newStatuses);
  };

  const applyRedactions = async () => {
    if (!snapshot) return;
    
    setIsApplying(true);
    try {
      const acceptedEntityIds = Object.entries(entityStatuses)
        .filter(([_, accepted]) => accepted)
        .map(([id, _]) => id);
      
      const response = await fetch(`http://localhost:7032/redaction/apply/${snapshot.snapshot_id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(acceptedEntityIds)
      });
      
      const result = await response.json();
      
      if (result.status === 'applied') {
        // Save redacted text to file
        await saveRedactedText(result.redacted_text);
        
        // Show success message
        alert(`Redaction applied successfully! ${result.entities_applied} entities redacted.`);
      }
      
    } catch (error) {
      console.error('Error applying redactions:', error);
      alert('Error applying redactions. Please try again.');
    } finally {
      setIsApplying(false);
    }
  };

  const saveRedactedText = async (redactedText: string) => {
    try {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const filename = `session_${timestamp}_redacted.txt`;
      
      // In a real Electron app, this would use the IPC bridge
      console.log('Would save redacted text to:', filename);
      
      // For now, trigger a download
      const blob = new Blob([redactedText], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
    } catch (error) {
      console.error('Error saving redacted text:', error);
    }
  };

  const getEntityColor = (label: string) => {
    const colors: Record<string, string> = {
      'PERSON': 'bg-red-100 border-red-300 text-red-800',
      'PHONE': 'bg-blue-100 border-blue-300 text-blue-800',
      'EMAIL': 'bg-green-100 border-green-300 text-green-800',
      'ADDRESS': 'bg-yellow-100 border-yellow-300 text-yellow-800',
      'DOB': 'bg-purple-100 border-purple-300 text-purple-800',
      'AGE': 'bg-indigo-100 border-indigo-300 text-indigo-800',
      'SSN': 'bg-red-200 border-red-400 text-red-900',
      'MRN': 'bg-orange-100 border-orange-300 text-orange-800',
      'ORG': 'bg-gray-100 border-gray-300 text-gray-800'
    };
    return colors[label] || 'bg-gray-100 border-gray-300 text-gray-800';
  };

  const getFilteredEntities = () => {
    if (!snapshot) return [];
    
    if (filterLabel === 'ALL') {
      return snapshot.entities;
    }
    
    return snapshot.entities.filter(entity => entity.label === filterLabel);
  };

  const getEntityLabels = () => {
    if (!snapshot) return [];
    return ['ALL', ...Array.from(new Set(snapshot.entities.map(e => e.label)))];
  };

  const getAcceptedCount = () => {
    return Object.values(entityStatuses).filter(Boolean).length;
  };

  const getTotalCount = () => {
    return snapshot?.entities.length || 0;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
        <span className="ml-2">Loading PHI analysis...</span>
      </div>
    );
  }

  if (!snapshot) {
    return (
      <div className="p-6">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium">No PHI Data Available</h3>
          <p className="text-gray-600 mt-2">
            Start recording to analyze transcription for PHI entities.
          </p>
          <button
            onClick={loadSnapshot}
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            Refresh
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="bg-white border-b p-4">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">PHI Review & Redaction</h2>
          
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-600">
              {getAcceptedCount()} of {getTotalCount()} entities selected
            </span>
            <button
              onClick={loadSnapshot}
              disabled={isLoading}
              className="p-2 text-gray-500 hover:text-gray-700"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        <div className="flex justify-between items-center">
          {/* Filter Controls */}
          <div className="flex items-center space-x-4">
            <select
              value={filterLabel}
              onChange={(e) => setFilterLabel(e.target.value)}
              className="px-3 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {getEntityLabels().map(label => (
                <option key={label} value={label}>{label}</option>
              ))}
            </select>
            
            <div className="flex space-x-2">
              <button
                onClick={() => toggleAllEntities(true)}
                className="px-3 py-1 text-sm bg-green-500 text-white rounded hover:bg-green-600"
              >
                Accept All
              </button>
              <button
                onClick={() => toggleAllEntities(false)}
                className="px-3 py-1 text-sm bg-red-500 text-white rounded hover:bg-red-600"
              >
                Reject All
              </button>
            </div>
          </div>

          {/* Preview Mode */}
          <div className="flex space-x-2">
            <button
              onClick={() => setPreviewMode('diff')}
              className={`px-3 py-1 text-sm rounded ${
                previewMode === 'diff' ? 'bg-blue-500 text-white' : 'bg-gray-200'
              }`}
            >
              Diff
            </button>
            <button
              onClick={() => setPreviewMode('redacted')}
              className={`px-3 py-1 text-sm rounded ${
                previewMode === 'redacted' ? 'bg-blue-500 text-white' : 'bg-gray-200'
              }`}
            >
              Redacted
            </button>
            <button
              onClick={() => setPreviewMode('original')}
              className={`px-3 py-1 text-sm rounded ${
                previewMode === 'original' ? 'bg-blue-500 text-white' : 'bg-gray-200'
              }`}
            >
              Original
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Entity List */}
        <div className="w-1/2 border-r overflow-y-auto">
          <div className="p-4">
            <h3 className="font-medium mb-3">Detected PHI Entities</h3>
            
            <div className="space-y-2">
              {getFilteredEntities().map((entity) => (
                <div
                  key={entity.id}
                  className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${
                    entityStatuses[entity.id] 
                      ? getEntityColor(entity.label) 
                      : 'bg-gray-50 border-gray-200 text-gray-500'
                  }`}
                  onClick={() => toggleEntity(entity.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-medium px-2 py-1 rounded bg-white bg-opacity-50">
                          {entity.label}
                        </span>
                        <span className="text-xs text-gray-600">
                          {(entity.confidence * 100).toFixed(0)}% • {entity.method}
                        </span>
                      </div>
                      
                      <div className="mt-2 font-mono text-sm">
                        "{entity.text}"
                      </div>
                      
                      {entity.contexts && entity.contexts.length > 0 && (
                        <div className="mt-2 text-xs text-gray-600">
                          Context: "{entity.contexts[0].context.substring(0, 60)}..."
                        </div>
                      )}
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      {entityStatuses[entity.id] ? (
                        <Check className="h-5 w-5 text-green-600" />
                      ) : (
                        <X className="h-5 w-5 text-red-600" />
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Preview Panel */}
        <div className="w-1/2 overflow-y-auto">
          <div className="p-4">
            <h3 className="font-medium mb-3">
              {previewMode === 'diff' ? 'Preview Diff' : 
               previewMode === 'redacted' ? 'Redacted Text' : 'Original Text'}
            </h3>
            
            <div className="bg-gray-50 p-4 rounded-lg font-mono text-sm whitespace-pre-wrap">
              {previewMode === 'diff' && snapshot.preview_diff}
              {previewMode === 'redacted' && snapshot.redacted_text}
              {previewMode === 'original' && 'Original text would be shown here...'}
            </div>
          </div>
        </div>
      </div>

      {/* Footer Actions */}
      <div className="bg-white border-t p-4">
        <div className="flex justify-between items-center">
          <div className="text-sm text-gray-600">
            Original: {snapshot.original_length} chars → 
            Redacted: {snapshot.redacted_length} chars
          </div>
          
          <button
            onClick={applyRedactions}
            disabled={isApplying || getAcceptedCount() === 0}
            className={`flex items-center space-x-2 px-6 py-2 rounded-lg font-medium ${
              isApplying || getAcceptedCount() === 0
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-500 text-white hover:bg-blue-600'
            }`}
          >
            {isApplying ? (
              <>
                <RefreshCw className="h-5 w-5 animate-spin" />
                <span>Applying...</span>
              </>
            ) : (
              <>
                <Save className="h-5 w-5" />
                <span>Save Redacted Text</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default PHIReview;