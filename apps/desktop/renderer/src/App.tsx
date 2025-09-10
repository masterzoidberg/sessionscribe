import React, { useState, useEffect } from 'react';
import Recorder from './components/Recorder';
import LiveTranscriber from './components/LiveTranscriber';
import PHIReview from './components/PHIReview';
import SessionWizard from './components/SessionWizard';
import NotePanel from './components/NotePanel';
import LiveDashboard from './components/LiveDashboard';

const App: React.FC = () => {
  const [currentStep, setCurrentStep] = useState<'record' | 'review' | 'note' | 'dashboard'>('record');

  // Ping test to validate Electron bridge
  useEffect(() => {
    if (window.electronAPI?.ping) {
      window.electronAPI.ping().then(result => {
        console.log('Electron Ping Test:', result);
      }).catch(err => {
        console.error('Electron Ping Test failed:', err);
      });
    }
  }, []);

  return (
    <div className="app bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex-shrink-0">
        <h1 className="text-2xl font-bold text-gray-900">SessionScribe</h1>
        <div className="flex space-x-4 mt-2">
          <button
            className={`px-3 py-1 rounded text-sm ${currentStep === 'record' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
            onClick={() => setCurrentStep('record')}
          >
            Record
          </button>
          <button
            className={`px-3 py-1 rounded text-sm ${currentStep === 'review' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
            onClick={() => setCurrentStep('review')}
          >
            Review
          </button>
          <button
            className={`px-3 py-1 rounded text-sm ${currentStep === 'note' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
            onClick={() => setCurrentStep('note')}
          >
            Note
          </button>
          <button
            className={`px-3 py-1 rounded text-sm ${currentStep === 'dashboard' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
            onClick={() => setCurrentStep('dashboard')}
          >
            Dashboard
          </button>
        </div>
      </header>

      <main className="main-content">
        {currentStep === 'record' && (
          <div className="h-full flex">
            <div className="flex-1 p-6 overflow-y-auto">
              <Recorder />
            </div>
            <div className="w-1/2 border-l border-gray-200 overflow-y-auto">
              <LiveTranscriber />
            </div>
          </div>
        )}

        {currentStep === 'review' && (
          <div className="p-6 h-full overflow-y-auto">
            <PHIReview />
          </div>
        )}

        {currentStep === 'note' && (
          <div className="h-full flex">
            <div className="flex-1 p-6 overflow-y-auto">
              <SessionWizard />
            </div>
            <div className="w-1/2 border-l border-gray-200 overflow-y-auto">
              <NotePanel />
            </div>
          </div>
        )}

        {currentStep === 'dashboard' && (
          <div className="p-6 h-full overflow-y-auto">
            <LiveDashboard />
          </div>
        )}
      </main>
    </div>
  );
};

export default App;