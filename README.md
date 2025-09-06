# SessionScribe

SessionScribe is a Windows desktop application for recording therapy sessions with live transcription, PHI redaction, and automated DAP note generation.

## Features

- **Dual Audio Recording**: Captures stereo audio (Therapist on left channel via microphone, Client on right channel via WASAPI loopback)
- **Live Transcription**: Real-time speech-to-text with <2s p95 latency using faster-whisper
- **PHI Redaction**: Automatic detection and redaction of personal health information using regex patterns and spaCy NER
- **DAP Note Generation**: Automated clinical note generation using OpenAI API with schema validation
- **Insights Dashboard**: Optional session insights extraction with offline/redaction gates
- **Privacy First**: Offline-capable, redaction-required before any network transmission

## Architecture

```
SessionScribe/
├── apps/desktop/
│   ├── electron/          # Electron main process & preload
│   └── renderer/          # React UI with Tailwind CSS
├── services/
│   ├── asr/              # Audio recording + Whisper transcription
│   ├── redaction/        # PHI detection & redaction
│   ├── note_builder/     # DAP note generation via OpenAI
│   └── insights_bridge/  # Session insights (optional)
├── packages/shared/
│   ├── schemas/          # JSON schemas for validation
│   └── prompts/          # LLM prompt templates
└── tests/                # Unit, integration & E2E tests
```

## Quick Start

### Prerequisites

- Windows 10/11
- Python 3.11+
- Node.js 18+ 
- pnpm

### Installation

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd SessionScribe
   ```

2. **Run development setup**:
   ```powershell
   .\scripts\dev.ps1
   ```

3. **Start the application**:
   ```bash
   # Terminal 1: Start all services
   make dev
   
   # Terminal 2: Start renderer 
   pnpm -C apps/desktop/renderer dev
   
   # Terminal 3: Start electron
   pnpm -C apps/desktop/electron dev
   ```

### Environment Configuration

Copy `.env.example` to `.env` and configure:

```env
OPENAI_API_KEY=your_api_key_here
SS_OFFLINE=false
SS_OUTPUT_DIR=%USERPROFILE%\Documents\SessionScribe
```

## Usage

### Recording Sessions

1. **Setup**: Select microphone device and session type
2. **Record**: Use Ctrl+Alt+R to start/stop recording 
3. **Mark**: Use Ctrl+Alt+M to bookmark important moments
4. **Monitor**: Watch live audio levels and transcription

### PHI Review

1. **Review**: Examine detected PHI entities with evidence
2. **Accept/Reject**: Approve or reject each redaction
3. **Save**: Generate redacted transcript file

### Note Generation

1. **Configure**: Choose session type and note template
2. **Generate**: Create DAP note from redacted transcript
3. **Validate**: Ensure note meets schema requirements
4. **Save**: Export note as plain text file

### Dashboard Insights (Optional)

1. **Quick Redact**: Process transcript for PHI
2. **Select**: Choose insight types (themes, questions, etc.)
3. **Confirm**: Review redaction before sending
4. **Send**: Get AI insights (requires online mode)

## File Outputs

SessionScribe saves files to `%USERPROFILE%\Documents\SessionScribe\`:

- `session_YYYYMMDD_HHMMSS_audio.wav` - Stereo recording
- `session_YYYYMMDD_HHMMSS_original.txt` - Raw transcript  
- `session_YYYYMMDD_HHMMSS_redacted.txt` - PHI-redacted transcript
- `session_YYYYMMDD_HHMMSS_note.txt` - Final DAP note

## Security & Privacy

- **Offline First**: Default mode with no network access
- **Redact Before Send**: PHI removal required before API calls
- **Local Storage**: All transcripts and notes saved locally only
- **No Telemetry**: Zero analytics or crash reporting
- **Content Isolation**: No logging of session content

## Development

### Testing

```bash
# Python unit tests
pytest

# React component tests  
pnpm -C apps/desktop/renderer test

# End-to-end tests
pnpm -C apps/desktop/renderer e2e

# Integration tests
pytest tests/test_integration.py
```

### Building

```bash
# Build for production
make build

# Create Windows installer
pnpm -C apps/desktop/electron build
```

## Quality Gates

- **Latency**: Live captions p95 ≤ 2.0 seconds
- **Redaction**: Precision ≥ 90%, Recall ≥ 95% 
- **Validation**: 100% JSON schema compliance
- **Security**: Zero PHI in logs or network requests

## License

[License information to be added]

## Support

For issues and feature requests, please use the GitHub issue tracker.