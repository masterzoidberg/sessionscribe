You are Claude Code. Read all files in /blueprints and /packages/shared.
Goal: Scaffold the SSS for SessionScribe (Windows) exactly per the component contracts.

Deliver in phases:
1) Monorepo layout (Electron/React app, FastAPI services, shared schemas/prompts).
2) Implement Recorder → LiveTranscriber → PHIRedactor (background+snapshot) → NoteBuilder (JSON→txt).
3) Implement InsightsBridge + DashboardUI (Quick Redact → Confirm → Send).
4) Add tests per /blueprints/TEST_PLAN.yaml. Enforce offline & redact-before-send gates.
5) Package Windows installer (NSIS). No telemetry.