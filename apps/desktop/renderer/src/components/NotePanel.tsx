import React, { useState, useEffect } from 'react';
import { FileText, Download, RefreshCw, CheckCircle, AlertCircle, Eye } from 'lucide-react';

interface DAPNote {
  session_type: string;
  data: string;
  assessment: string;
  plan: string;
  risk_flags: string[];
  followups: string[];
}

interface NoteGenerationResult {
  dap_json: DAPNote;
  validation_status: 'valid' | 'invalid' | 'repaired';
  validation_errors: string[];
  note_text: string;
  file_path?: string;
}

const NotePanel: React.FC = () => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedNote, setGeneratedNote] = useState<NoteGenerationResult | null>(null);
  const [showJson, setShowJson] = useState(false);
  const [redactedText, setRedactedText] = useState<string>('');
  
  useEffect(() => {
    loadRedactedText();
  }, []);

  const loadRedactedText = async () => {
    try {
      // In a real app, this would load the latest redacted text
      // For now, we'll simulate it
      const mockText = "This is a sample redacted transcript...";
      setRedactedText(mockText);
    } catch (error) {
      console.error('Error loading redacted text:', error);
    }
  };

  const generateNote = async () => {
    if (!redactedText.trim()) {
      alert('No redacted transcript available. Please complete PHI review first.');
      return;
    }

    setIsGenerating(true);
    try {
      // Get session configuration (would come from SessionWizard)
      const sessionConfig = {
        session_type: 'Individual',
        prompt_version: 'default'
      };

      const response = await fetch('http://localhost:7034/note/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          transcript_redacted: redactedText,
          ...sessionConfig
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      setGeneratedNote(result);

    } catch (error) {
      console.error('Error generating note:', error);
      alert('Error generating note. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  const saveNote = async () => {
    if (!generatedNote) return;

    try {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const filename = `session_${timestamp}_note.txt`;

      // In a real Electron app, this would use the IPC bridge to save files
      console.log('Would save note to:', filename);

      // For now, trigger a download
      const blob = new Blob([generatedNote.note_text], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      alert('Note saved successfully!');

    } catch (error) {
      console.error('Error saving note:', error);
      alert('Error saving note. Please try again.');
    }
  };

  const getValidationIcon = () => {
    if (!generatedNote) return null;
    
    switch (generatedNote.validation_status) {
      case 'valid':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'repaired':
        return <AlertCircle className="h-5 w-5 text-yellow-600" />;
      case 'invalid':
        return <AlertCircle className="h-5 w-5 text-red-600" />;
      default:
        return null;
    }
  };

  const getValidationMessage = () => {
    if (!generatedNote) return '';
    
    switch (generatedNote.validation_status) {
      case 'valid':
        return 'Note validates against DAP schema';
      case 'repaired':
        return 'Note was repaired to match schema';
      case 'invalid':
        return 'Note failed validation';
      default:
        return '';
    }
  };

  const renderNotePreview = () => {
    if (!generatedNote) return null;

    return (
      <div className="space-y-4">
        {/* Validation Status */}
        <div className="flex items-center space-x-2 p-3 bg-gray-50 rounded-lg">
          {getValidationIcon()}
          <span className="text-sm font-medium">{getValidationMessage()}</span>
          
          <button
            onClick={() => setShowJson(!showJson)}
            className="ml-auto flex items-center space-x-1 text-xs text-gray-600 hover:text-gray-800"
          >
            <Eye className="h-4 w-4" />
            <span>{showJson ? 'Hide' : 'Show'} JSON</span>
          </button>
        </div>

        {/* JSON View */}
        {showJson && (
          <div className="bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-xs overflow-auto max-h-64">
            <pre>{JSON.stringify(generatedNote.dap_json, null, 2)}</pre>
          </div>
        )}

        {/* Validation Errors */}
        {generatedNote.validation_errors.length > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <h4 className="text-sm font-medium text-red-800 mb-2">Validation Issues:</h4>
            <ul className="text-xs text-red-700 space-y-1">
              {generatedNote.validation_errors.map((error, index) => (
                <li key={index}>• {error}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Note Text Preview */}
        <div className="bg-white border rounded-lg p-4">
          <h4 className="font-medium mb-3">Generated Note Preview:</h4>
          <div className="prose prose-sm max-w-none">
            <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">
              {generatedNote.note_text}
            </pre>
          </div>
        </div>

        {/* Note Statistics */}
        <div className="grid grid-cols-3 gap-4 text-center">
          <div className="bg-gray-50 p-3 rounded-lg">
            <div className="text-lg font-bold text-gray-900">
              {generatedNote.note_text.length}
            </div>
            <div className="text-xs text-gray-600">Characters</div>
          </div>
          
          <div className="bg-gray-50 p-3 rounded-lg">
            <div className="text-lg font-bold text-gray-900">
              {generatedNote.dap_json.risk_flags?.length || 0}
            </div>
            <div className="text-xs text-gray-600">Risk Flags</div>
          </div>
          
          <div className="bg-gray-50 p-3 rounded-lg">
            <div className="text-lg font-bold text-gray-900">
              {generatedNote.dap_json.followups?.length || 0}
            </div>
            <div className="text-xs text-gray-600">Follow-ups</div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="border-b p-4">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-semibold">DAP Note Generation</h2>
          
          <div className="flex space-x-2">
            {generatedNote && (
              <button
                onClick={saveNote}
                className="flex items-center space-x-2 px-3 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
              >
                <Download className="h-4 w-4" />
                <span>Save Note</span>
              </button>
            )}
            
            <button
              onClick={generateNote}
              disabled={isGenerating || !redactedText.trim()}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg font-medium ${
                isGenerating || !redactedText.trim()
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-blue-500 text-white hover:bg-blue-600'
              }`}
            >
              {isGenerating ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  <span>Generating...</span>
                </>
              ) : (
                <>
                  <FileText className="h-4 w-4" />
                  <span>Generate Note</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {!generatedNote && !isGenerating && (
          <div className="text-center py-12">
            <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Note Generated</h3>
            <p className="text-gray-600 mb-6">
              Complete the session setup and PHI review, then generate your DAP note.
            </p>
            
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-left max-w-md mx-auto">
              <h4 className="font-medium text-blue-800 mb-2">Note Generation Process:</h4>
              <ol className="text-sm text-blue-700 space-y-1">
                <li>1. Record and transcribe session</li>
                <li>2. Review and approve PHI redactions</li>
                <li>3. Configure session type and template</li>
                <li>4. Generate and validate DAP note</li>
                <li>5. Save note to file system</li>
              </ol>
            </div>
          </div>
        )}

        {isGenerating && (
          <div className="text-center py-12">
            <RefreshCw className="h-12 w-12 text-blue-500 mx-auto mb-4 animate-spin" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Generating Note...</h3>
            <p className="text-gray-600">
              Processing redacted transcript with OpenAI to create your DAP note.
            </p>
          </div>
        )}

        {generatedNote && renderNotePreview()}
      </div>

      {/* Footer */}
      <div className="border-t p-3 text-xs text-gray-500 text-center">
        {redactedText ? (
          <>Input: {redactedText.length} characters of redacted transcript</>
        ) : (
          <>No redacted transcript available. Complete PHI review first.</>
        )}
      </div>
    </div>
  );
};

export default NotePanel;