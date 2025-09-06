import React, { useState, useEffect } from 'react';
import { ChevronRight, FileText, Settings, User, Users, Heart } from 'lucide-react';

interface SessionWizardProps {
  onSessionUpdate?: (data: any) => void;
}

type SessionType = 'Individual' | 'Intake' | 'Couples' | 'Family';

interface PromptTemplate {
  id: string;
  name: string;
  content: string;
  session_type: SessionType;
}

const SessionWizard: React.FC<SessionWizardProps> = ({ onSessionUpdate }) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [sessionType, setSessionType] = useState<SessionType>('Individual');
  const [selectedPrompt, setSelectedPrompt] = useState<string>('default');
  const [customPrompt, setCustomPrompt] = useState<string>('');
  const [prompts, setPrompts] = useState<PromptTemplate[]>([]);
  
  const sessionTypes: { value: SessionType; label: string; icon: any; description: string }[] = [
    {
      value: 'Individual',
      label: 'Individual Therapy',
      icon: User,
      description: 'One-on-one therapy session'
    },
    {
      value: 'Intake',
      label: 'Initial Intake',
      icon: FileText,
      description: 'First session assessment'
    },
    {
      value: 'Couples',
      label: 'Couples Therapy',
      icon: Heart,
      description: 'Relationship counseling session'
    },
    {
      value: 'Family',
      label: 'Family Therapy',
      icon: Users,
      description: 'Family counseling session'
    }
  ];

  useEffect(() => {
    loadPromptTemplates();
  }, []);

  useEffect(() => {
    if (onSessionUpdate) {
      onSessionUpdate({
        sessionType,
        selectedPrompt,
        customPrompt
      });
    }
  }, [sessionType, selectedPrompt, customPrompt, onSessionUpdate]);

  const loadPromptTemplates = async () => {
    try {
      // In a real app, this would load from settings or API
      const defaultPrompts: PromptTemplate[] = [
        {
          id: 'default',
          name: 'Default DAP Template',
          content: 'Standard DAP note format focusing on clinical presentation, interventions, and plan.',
          session_type: 'Individual'
        },
        {
          id: 'intake',
          name: 'Intake Assessment Template',
          content: 'Comprehensive initial assessment including background, presenting issues, and treatment planning.',
          session_type: 'Intake'
        },
        {
          id: 'couples',
          name: 'Couples Therapy Template',
          content: 'Relationship dynamics, communication patterns, and intervention strategies.',
          session_type: 'Couples'
        },
        {
          id: 'family',
          name: 'Family Systems Template',
          content: 'Family dynamics, system interactions, and family-focused interventions.',
          session_type: 'Family'
        }
      ];
      
      setPrompts(defaultPrompts);
      
      // Set default prompt based on session type
      const defaultForType = defaultPrompts.find(p => p.session_type === sessionType);
      if (defaultForType) {
        setSelectedPrompt(defaultForType.id);
      }
      
    } catch (error) {
      console.error('Error loading prompt templates:', error);
    }
  };

  const handleSessionTypeChange = (type: SessionType) => {
    setSessionType(type);
    
    // Update prompt selection based on session type
    const matching = prompts.find(p => p.session_type === type);
    if (matching) {
      setSelectedPrompt(matching.id);
    }
  };

  const getFilteredPrompts = () => {
    return prompts.filter(p => p.session_type === sessionType || p.id === 'default');
  };

  const handleNext = () => {
    if (currentStep < 3) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const renderSessionTypeStep = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium mb-2">Select Session Type</h3>
        <p className="text-gray-600 text-sm">
          Choose the type of therapy session to customize the note template.
        </p>
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        {sessionTypes.map((type) => {
          const IconComponent = type.icon;
          return (
            <button
              key={type.value}
              onClick={() => handleSessionTypeChange(type.value)}
              className={`p-4 border-2 rounded-lg text-left transition-all ${
                sessionType === type.value
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center space-x-3">
                <IconComponent className={`h-6 w-6 ${
                  sessionType === type.value ? 'text-blue-600' : 'text-gray-500'
                }`} />
                <div>
                  <div className="font-medium">{type.label}</div>
                  <div className="text-sm text-gray-600">{type.description}</div>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );

  const renderPromptSelectionStep = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium mb-2">Choose Note Template</h3>
        <p className="text-gray-600 text-sm">
          Select a template for generating your DAP note from the session transcript.
        </p>
      </div>
      
      <div className="space-y-3">
        {getFilteredPrompts().map((prompt) => (
          <label
            key={prompt.id}
            className={`block p-4 border rounded-lg cursor-pointer transition-all ${
              selectedPrompt === prompt.id
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <input
              type="radio"
              name="prompt"
              value={prompt.id}
              checked={selectedPrompt === prompt.id}
              onChange={(e) => setSelectedPrompt(e.target.value)}
              className="sr-only"
            />
            <div>
              <div className="font-medium mb-1">{prompt.name}</div>
              <div className="text-sm text-gray-600">{prompt.content}</div>
            </div>
          </label>
        ))}
        
        <label
          className={`block p-4 border rounded-lg cursor-pointer transition-all ${
            selectedPrompt === 'custom'
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-200 hover:border-gray-300'
          }`}
        >
          <input
            type="radio"
            name="prompt"
            value="custom"
            checked={selectedPrompt === 'custom'}
            onChange={(e) => setSelectedPrompt(e.target.value)}
            className="sr-only"
          />
          <div>
            <div className="font-medium mb-1">Custom Template</div>
            <div className="text-sm text-gray-600">Create your own note template</div>
          </div>
        </label>
      </div>
    </div>
  );

  const renderCustomPromptStep = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium mb-2">Custom Note Template</h3>
        <p className="text-gray-600 text-sm">
          Enter your custom template instructions for generating the DAP note.
        </p>
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Template Instructions
        </label>
        <textarea
          value={customPrompt}
          onChange={(e) => setCustomPrompt(e.target.value)}
          placeholder="Enter instructions for how you want the DAP note to be structured and what should be emphasized..."
          className="w-full h-40 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
        />
        <div className="mt-2 text-xs text-gray-500">
          Variables available: {'{'}transcript_redacted{'}'}, {'{'}session_type{'}'}
        </div>
      </div>
      
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <h4 className="font-medium text-yellow-800 mb-2">Template Guidelines</h4>
        <ul className="text-sm text-yellow-700 space-y-1">
          <li>• Focus on clinical observations and interventions</li>
          <li>• Use neutral, professional language</li>
          <li>• Include specific treatment goals and plans</li>
          <li>• Maintain confidentiality and avoid identifying details</li>
        </ul>
      </div>
    </div>
  );

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return renderSessionTypeStep();
      case 2:
        return renderPromptSelectionStep();
      case 3:
        return selectedPrompt === 'custom' ? renderCustomPromptStep() : renderPromptSelectionStep();
      default:
        return renderSessionTypeStep();
    }
  };

  const canProceed = () => {
    switch (currentStep) {
      case 1:
        return sessionType !== '';
      case 2:
        return selectedPrompt !== '';
      case 3:
        return selectedPrompt !== 'custom' || customPrompt.trim() !== '';
      default:
        return false;
    }
  };

  return (
    <div className="bg-white rounded-lg p-6 shadow-sm border">
      <div className="mb-6">
        <h2 className="text-xl font-semibold mb-2">Session Setup</h2>
        
        {/* Progress Steps */}
        <div className="flex items-center space-x-4 mb-6">
          <div className={`flex items-center ${currentStep >= 1 ? 'text-blue-600' : 'text-gray-400'}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
              currentStep >= 1 ? 'bg-blue-600 text-white' : 'bg-gray-200'
            }`}>
              1
            </div>
            <span className="ml-2 text-sm font-medium">Session Type</span>
          </div>
          
          <ChevronRight className="h-4 w-4 text-gray-400" />
          
          <div className={`flex items-center ${currentStep >= 2 ? 'text-blue-600' : 'text-gray-400'}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
              currentStep >= 2 ? 'bg-blue-600 text-white' : 'bg-gray-200'
            }`}>
              2
            </div>
            <span className="ml-2 text-sm font-medium">Note Template</span>
          </div>
          
          {selectedPrompt === 'custom' && (
            <>
              <ChevronRight className="h-4 w-4 text-gray-400" />
              <div className={`flex items-center ${currentStep >= 3 ? 'text-blue-600' : 'text-gray-400'}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  currentStep >= 3 ? 'bg-blue-600 text-white' : 'bg-gray-200'
                }`}>
                  3
                </div>
                <span className="ml-2 text-sm font-medium">Custom Template</span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Step Content */}
      <div className="mb-8">
        {renderStepContent()}
      </div>

      {/* Navigation */}
      <div className="flex justify-between">
        <button
          onClick={handlePrevious}
          disabled={currentStep === 1}
          className={`px-4 py-2 rounded-lg font-medium ${
            currentStep === 1
              ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          Previous
        </button>
        
        <div className="flex items-center space-x-2">
          <div className="text-sm text-gray-500">
            Selected: {sessionType} • {selectedPrompt === 'custom' ? 'Custom' : 'Template'}
          </div>
          
          {(currentStep < 3 && selectedPrompt !== 'custom') || (currentStep < 3 && selectedPrompt === 'custom') ? (
            <button
              onClick={handleNext}
              disabled={!canProceed()}
              className={`px-4 py-2 rounded-lg font-medium ${
                !canProceed()
                  ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  : 'bg-blue-500 text-white hover:bg-blue-600'
              }`}
            >
              Next
            </button>
          ) : (
            <button
              className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 font-medium"
            >
              Ready to Generate Note
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default SessionWizard;