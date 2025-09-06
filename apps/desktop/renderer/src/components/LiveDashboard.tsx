import React, { useState, useEffect } from 'react';
import { Send, RefreshCw, AlertCircle, CheckCircle, X, Eye, EyeOff } from 'lucide-react';

interface InsightsStatus {
  available: boolean;
  offline_mode: boolean;
  redact_before_send: boolean;
  provider: string;
}

interface InsightsResponse {
  themes?: string[];
  questions?: string[];
  missing?: string[];
  homework?: string[];
  risk_flags?: string[];
}

const LiveDashboard: React.FC = () => {
  const [status, setStatus] = useState<InsightsStatus | null>(null);
  const [currentSnapshot, setCurrentSnapshot] = useState<string | null>(null);
  const [insights, setInsights] = useState<InsightsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedInsights, setSelectedInsights] = useState<Set<string>>(new Set());
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  
  const insightTypes = [
    { key: 'themes', label: 'Session Themes', icon: '🎯', description: 'Key therapeutic themes discussed' },
    { key: 'questions', label: 'Follow-up Questions', icon: '❓', description: 'Questions for next session' },
    { key: 'missing', label: 'Missing Information', icon: '⚠️', description: 'Important details not addressed' },
    { key: 'homework', label: 'Homework Assignments', icon: '📝', description: 'Tasks for client between sessions' },
    { key: 'risk_flags', label: 'Risk Indicators', icon: '🚨', description: 'Safety concerns or risk factors' }
  ];

  useEffect(() => {
    loadInsightsStatus();
    loadLatestSnapshot();
  }, []);

  const loadInsightsStatus = async () => {
    try {
      const response = await fetch('http://localhost:7033/insights/status');
      const statusData = await response.json();
      setStatus(statusData);
    } catch (error) {
      console.error('Error loading insights status:', error);
    }
  };

  const loadLatestSnapshot = async () => {
    try {
      // Get the latest snapshot from redaction service
      const response = await fetch('http://localhost:7032/redaction/snapshot');
      const snapshot = await response.json();
      setCurrentSnapshot(snapshot.snapshot_id);
    } catch (error) {
      console.error('Error loading snapshot:', error);
    }
  };

  const handleQuickRedact = async () => {
    setIsLoading(true);
    try {
      // Trigger a quick redaction process
      await fetch('http://localhost:7032/redaction/process-slow', {
        method: 'POST'
      });
      
      // Get updated snapshot
      await loadLatestSnapshot();
      
    } catch (error) {
      console.error('Error during quick redaction:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleInsightSelection = (insightType: string) => {
    setSelectedInsights(prev => {
      const newSet = new Set(prev);
      if (newSet.has(insightType)) {
        newSet.delete(insightType);
      } else {
        newSet.add(insightType);
      }
      return newSet;
    });
  };

  const handleConfirmSend = () => {
    setShowConfirmModal(true);
  };

  const sendForInsights = async () => {
    if (!currentSnapshot || selectedInsights.size === 0) return;
    
    setIsLoading(true);
    setShowConfirmModal(false);
    
    try {
      const response = await fetch('http://localhost:7033/insights/send', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          snapshot_id: currentSnapshot,
          ask_for: Array.from(selectedInsights)
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const insightsData = await response.json();
      setInsights(insightsData);
      
    } catch (error) {
      console.error('Error getting insights:', error);
      alert('Error getting insights. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const canSend = () => {
    return (
      status?.available && 
      currentSnapshot && 
      selectedInsights.size > 0 && 
      !isLoading
    );
  };

  const getStatusMessage = () => {
    if (!status) return 'Loading status...';
    
    if (status.offline_mode) {
      return 'Dashboard disabled - offline mode enabled';
    }
    
    if (!status.redact_before_send) {
      return 'Dashboard disabled - redaction required';
    }
    
    if (!currentSnapshot) {
      return 'No redacted snapshot available';
    }
    
    if (selectedInsights.size === 0) {
      return 'Select insights to request';
    }
    
    return 'Ready to send for insights';
  };

  const renderConfirmModal = () => {
    if (!showConfirmModal) return null;

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
          <h3 className="text-lg font-semibold mb-4">Confirm Insights Request</h3>
          
          <div className="mb-4">
            <p className="text-sm text-gray-600 mb-3">
              You are about to send redacted session data to OpenAI for analysis. Selected insights:
            </p>
            <ul className="text-sm space-y-1">
              {Array.from(selectedInsights).map(type => {
                const insightType = insightTypes.find(i => i.key === type);
                return (
                  <li key={type} className="flex items-center space-x-2">
                    <span>{insightType?.icon}</span>
                    <span>{insightType?.label}</span>
                  </li>
                );
              })}
            </ul>
          </div>
          
          <div className="bg-blue-50 border border-blue-200 rounded p-3 mb-4">
            <p className="text-xs text-blue-800">
              ✓ Only redacted data will be sent<br />
              ✓ No PHI will be transmitted<br />
              ✓ Response is view-only (not saved to disk)
            </p>
          </div>
          
          <div className="flex space-x-3">
            <button
              onClick={() => setShowConfirmModal(false)}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={sendForInsights}
              className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
            >
              Send for Insights
            </button>
          </div>
        </div>
      </div>
    );
  };

  const renderInsightsResults = () => {
    if (!insights) return null;

    return (
      <div className="bg-white rounded-lg border p-4">
        <h3 className="font-semibold mb-4">Session Insights</h3>
        
        <div className="space-y-4">
          {insightTypes.map(type => {
            const data = insights[type.key as keyof InsightsResponse];
            if (!data || data.length === 0) return null;
            
            return (
              <div key={type.key} className="border-l-4 border-blue-200 pl-4">
                <div className="flex items-center space-x-2 mb-2">
                  <span>{type.icon}</span>
                  <h4 className="font-medium">{type.label}</h4>
                </div>
                <ul className="space-y-1">
                  {data.map((item, index) => (
                    <li key={index} className="text-sm text-gray-700">
                      • {item}
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
        
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded text-sm">
          <p className="text-yellow-800">
            <strong>Note:</strong> These insights are AI-generated suggestions for clinical consideration.
            They are not diagnostic recommendations and should be reviewed by the clinician.
          </p>
        </div>
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="bg-white border-b p-4">
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-semibold">Live Dashboard</h2>
          
          <div className="flex items-center space-x-4">
            {/* Status Indicator */}
            <div className="flex items-center space-x-2">
              {status?.available ? (
                <CheckCircle className="h-5 w-5 text-green-600" />
              ) : (
                <AlertCircle className="h-5 w-5 text-red-600" />
              )}
              <span className="text-sm text-gray-600">
                {status?.provider || 'OpenAI'}
              </span>
            </div>
            
            <button
              onClick={loadInsightsStatus}
              className="p-2 text-gray-500 hover:text-gray-700"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 p-6 space-y-6">
        {/* Quick Actions */}
        <div className="bg-white rounded-lg border p-4">
          <h3 className="font-semibold mb-4">Quick Actions</h3>
          
          <div className="flex space-x-4">
            <button
              onClick={handleQuickRedact}
              disabled={isLoading}
              className="flex items-center space-x-2 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 disabled:opacity-50"
            >
              {isLoading ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
              <span>Quick Redact</span>
            </button>
            
            <div className="text-sm text-gray-600 flex items-center">
              Snapshot: {currentSnapshot ? currentSnapshot.substring(0, 8) + '...' : 'None'}
            </div>
          </div>
        </div>

        {/* Insights Selection */}
        <div className="bg-white rounded-lg border p-4">
          <h3 className="font-semibold mb-4">Request Insights</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            {insightTypes.map(type => (
              <label
                key={type.key}
                className={`flex items-start space-x-3 p-3 border rounded-lg cursor-pointer transition-all ${
                  selectedInsights.has(type.key)
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedInsights.has(type.key)}
                  onChange={() => toggleInsightSelection(type.key)}
                  className="mt-1"
                />
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-lg">{type.icon}</span>
                    <span className="font-medium">{type.label}</span>
                  </div>
                  <p className="text-sm text-gray-600 mt-1">
                    {type.description}
                  </p>
                </div>
              </label>
            ))}
          </div>
          
          {/* Send Button */}
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-600">
              {getStatusMessage()}
            </p>
            
            <button
              onClick={handleConfirmSend}
              disabled={!canSend()}
              className={`flex items-center space-x-2 px-6 py-2 rounded-lg font-medium ${
                canSend()
                  ? 'bg-blue-500 text-white hover:bg-blue-600'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
            >
              {isLoading ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              <span>
                {isLoading ? 'Processing...' : 'Confirm & Send'}
              </span>
            </button>
          </div>
        </div>

        {/* Results */}
        {renderInsightsResults()}
      </div>

      {/* Confirmation Modal */}
      {renderConfirmModal()}
    </div>
  );
};

export default LiveDashboard;