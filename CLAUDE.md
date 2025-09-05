# CLAUDE.md — SessionScribe (Windows) Build Contract

You are **Claude Code**. Implement the *Smallest Shippable Slice (SSS)* for **SessionScribe**: a Windows-only desktop app that records stereo (Mic + WASAPI Loopback), shows live captions, performs PHI redaction, generates a DAP note from an editable prompt, and (optionally) sends a **redacted snapshot** to the OpenAI API for dashboard insights. Save plain text artifacts only.

---

## RIPER (Role • Inputs • Process • Expectations • Results)

**ROLE**  
- Primary implementer for UI (Electron/React), Python services (FastAPI), tests (Jest/Playwright/Pytest), and packaging (electron-builder NSIS).  
- Follow all contracts in `/blueprints` and schemas/prompts in `/packages/shared`.

**INPUTS**  
- `/blueprints/*.yaml` (ARCHITECTURE, TASK_GRAPH, TEST_PLAN, AGENT_RUNBOOKS, DEPLOY_PLAYBOOK, SECURITY_COMPLIANCE)  
- `/blueprints/COMPONENTS/*.yaml` (Recorder, LiveTranscriber, PHIRedactor, NoteBuilder, InsightsBridge, DashboardUI)  
- `/packages/shared/schemas/*.json` (note.dap.schema.json, insights.schema.json)  
- `/packages/shared/prompts/*.md` (DAP.default.md, Insights.default.md)  
- `.env.example` (environment configuration)

**PROCESS (strict order)**  
1. **Scaffold** monorepo layout (see Repo Map) and wire secure IPC.  
2. Implement **Recorder → LiveTranscriber → PHIRedactor (background+snapshot) → NoteBuilder (JSON→txt)**.  
3. Implement **InsightsBridge + DashboardUI**: *Quick Redact → Confirm → Send* (optional).  
4. Add tests from `/blueprints/TEST_PLAN.yaml` and enforce gates from `/blueprints/AGENT_RUNBOOKS.yaml`.  
5. Package Windows installer (NSIS). No telemetry.

**EXPECTATIONS / QUALITY GATES**  
- ✅ **Offline default**: *no network egress* when `SS_OFFLINE=true`.  
- ✅ **Redact-before-send**: Only **redacted snapshots** can be sent to API.  
- ✅ **Schema enforcement**: Note JSON **must** validate against `note.dap.schema.json` before saving `_note.txt`.  
- ✅ **Latency**: Live caption **p95 ≤ 2.0 s** on target machine.  
- ✅ **Redaction**: seeded PHI tests **recall ≥ 0.95, precision ≥ 0.90**.  
- ✅ **Artifacts**: write only `.wav`, `_original.txt`, `_redacted.txt`, `_note.txt` (plus optional per-channel `.txt` if enabled).  
- ❌ **Never** log content (transcripts/notes); only minimal metadata in local rotating debug logs.

**RESULTS**  
- A runnable SSS that satisfies **Acceptance Criteria** in `/blueprints/ARCHITECTURE.yaml` and all tests green.

---

## Repo Map (create these)

```

.
├─ apps/
│  └─ desktop/
│     ├─ electron/            # main.ts, preload.ts, builder.config.js
│     └─ renderer/            # React + Tailwind components
├─ services/
│  ├─ asr/                    # FastAPI WS /transcribe, Whisper
│  ├─ redaction/              # /redaction ingest + snapshot
│  └─ insights\_bridge/        # /insights/send → OpenAI JSON-only
├─ packages/
│  └─ shared/
│     ├─ schemas/             # note.dap.schema.json, insights.schema.json
│     └─ prompts/             # DAP.default.md, Insights.default.md
├─ blueprints/                # all project and component blueprints
├─ scripts/                   # dev.ps1
├─ .env.example
├─ pnpm-workspace.yaml
└─ Makefile

```

---

## Golden Rules (do not violate)

1. **Windows-only**. Audio = **48 kHz, 16-bit PCM stereo WAV**. Channel map: **L=Therapist (Mic)**, **R=Client (Loopback)**.  
2. **Offline first**. If `SS_OFFLINE=true`, block all outbound HTTP.  
3. **Redact-before-send**. Only **/redaction/snapshot** output is eligible for `/insights/send`.  
4. **No content logs**. Never write transcript/note content to logs or DB. Minimal metadata only.  
5. **Strict schemas**. Use JSON Schema **v2020-12** for DAP and insights. Reject or repair once; otherwise block.  
6. **Deterministic UI**. Buttons disabled unless gates pass (offline false, snapshot present, size ≤ max chars).  
7. **Least privilege**. No eval, `contextIsolation: true`, no `remote` module, CSP applied.

---

## Implementation Order (step-by-step)

1) **Electron shell**  
- `apps/desktop/electron/main.ts`: Single-instance lock, file protocol for local folders, secure IPC bridge.  
- `preload.ts`: Expose safe methods (`record.start/stop`, `settings.get/set`, `note.save`, `dashboard.send`).

2) **Recorder (WASAPI)**  
- `services/asr/audio_wasapi.py`: Open Mic + Loopback; timestamp alignment; write **stereo WAV**; provide PCM frames to transcriber.

3) **LiveTranscriber (Whisper)**  
- `services/asr/whisper_stream.py`: faster-whisper (CUDA if available), VAD chunking; stream partials `{channel, text, t0, t1}` via WS `/transcribe`.  
- UI `LiveTranscriber.tsx`: two lanes or single lane with `[T:] / [C:]` tags; p95 latency ≤ 2s.

4) **PHIRedactor (background + snapshot)**  
- `services/redaction/app.py`:  
  - **Fast lane (regex)** per chunk; **Slow lane (spaCy NER)** on cadence.  
  - Maintain rolling **EntityIndex** and **redacted_draft**.  
  - `GET /redaction/snapshot` → `{snapshot_id, preview_diff, entities}` (see schema).  
- UI `PHIReview.tsx`: entity list + evidence diff; accept/reject; writes `*_redacted.txt`.

5) **NoteBuilder**  
- Use `/packages/shared/prompts/DAP.default.md`.  
- Call OpenAI **only** with **redacted text** if online; otherwise local path placeholder.  
- Validate output against `note.dap.schema.json`, repair once if needed, render **plain text** to `*_note.txt`.

6) **InsightsBridge + DashboardUI** (optional; view-only)  
- UI `LiveDashboard.tsx`: **Quick Redact → Confirm → Send** panel with checkboxes `[themes, questions, missing, homework, risk]`.  
- `services/insights_bridge/app.py`:  
  - Accept `{snapshot_id, ask_for[]}`; resolve redacted text from snapshot store.  
  - Build compact JSON-only prompt from `/packages/shared/prompts/Insights.default.md`.  
  - Call OpenAI; validate response against `insights.schema.json`; drop invalid or unrepairable.

7) **Packaging**  
- `electron-builder` NSIS; first-run wizard to pick output folder; default to `%USERPROFILE%\Documents\SessionScribe`.

---

## Endpoints & Contracts (must match)

### `/transcribe` (WebSocket)  
- **In**: streaming PCM frames (L/R) metadata.  
- **Out**: `{ channel: "therapist"|"client", text: string, t0: number, t1: number }` partials.

### `/redaction/snapshot` (GET)  
- **Out**: per `/packages/shared/schemas/redaction.preview.schema.json` (entities, preview diff, lengths, `snapshot_id`).

### `/insights/send` (POST)  
- **In**: `{ snapshot_id: string, ask_for: string[] }` where ask_for ⊆ `["themes","questions","missing","homework","risk_flags"]`  
- **Out**: `insights.schema.json` (strict).

---

## UI Contracts

- **Recorder.tsx**: device pickers, meters, hotkeys (`Ctrl+Alt+R` start/stop, `Ctrl+Alt+M` mark).  
- **LiveTranscriber.tsx**: two lanes or tags; timestamps; copy buttons (no disk writes).  
- **PHIReview.tsx**: entity list with labels (`PERSON, PHONE, EMAIL, ADDRESS, DOB, AGE, SSN, MRN, ORG, SCHOOL, HANDLE`), accept/reject; save `_redacted.txt`.  
- **SessionWizard.tsx**: session type select (`Individual|Intake|Couples|Family`), prompt pick.  
- **PromptEditor.tsx**: load/save named prompt versions (stored in SQLite settings, not bundled secrets).  
- **NotePanel.tsx**: shows JSON validity status, preview of final note text; save `_note.txt`.  
- **LiveDashboard.tsx**: **Quick Redact → Confirm → Send** buttons, disabled until gates pass; show last response only; no disk saves.

---

## Environment & Defaults

Put these keys in `.env` (or use the provided `.env.example`):

```

OPENAI\_API\_KEY=
OPENAI\_BASE\_URL=[https://api.openai.com/v1](https://api.openai.com/v1)

SS\_OUTPUT\_DIR=%USERPROFILE%\Documents\SessionScribe
SS\_OFFLINE=true
SS\_REDACT\_BEFORE\_SEND=true
SS\_DASHBOARD\_PROVIDER=openai\_api
SS\_NOTE\_MODEL=gpt-4o-mini
SS\_NOTE\_TEMPERATURE=0.2
SS\_REGION=us
SS\_MAX\_SNAPSHOTS\_PER\_SESSION=12

```

---

## Commands

**Dev**
```

pnpm i

# terminals:

uvicorn services.asr.app\:app --reload --port 7031
uvicorn services.redaction.app\:app --reload --port 7032
uvicorn services.insights\_bridge.app\:app --reload --port 7033
pnpm -C apps/desktop/renderer dev
pnpm -C apps/desktop/electron dev

```

**Tests**
```

pytest -q
pnpm -C apps/desktop/renderer test
pnpm -C apps/desktop/renderer e2e   # Playwright

```

**Package**
```

pnpm -C apps/desktop/electron build

```

---

## Coding Standards

- **TypeScript**: `"strict": true`; ESLint + Prettier; no implicit `any`.  
- **Python**: 3.11+, type hints; Ruff + Black; pytest with fixtures and golden files.  
- **Security**: `contextIsolation: true`, disable `eval`, no `remote`, CSP in renderer.

---

## Tests to Implement (minimum)

- **Unit (Python)**: VAD chunking, regex detectors, NER merger, snapshot latency (`≤150 ms` on 6–8k chars).  
- **Unit (TS)**: reducer/store logic for captions and entity accept/reject.  
- **Integration**: stereo WAV fixture → captions p95 ≤ 2s; snapshot → confirm → send gate flow; DAP JSON valid then render to text.  
- **E2E (Playwright)**: hotkeys record/stop; PHIReview apply; SessionWizard generate/save note; Dashboard send disabled when offline or no snapshot.

---

## Acceptance Criteria (must pass)

- Start/Stop records **stereo WAV**; live captions appear with **p95 ≤ 2.0 s**.  
- Saving stops writes `*_original.txt`; PHIReview writes `*_redacted.txt`.  
- Wizard + Prompt → **DAP JSON validates** → writes `*_note.txt`.  
- Dashboard buttons only send **redacted snapshots**; responses validate against `insights.schema.json`; **no dashboard data is written to disk**.  
- When `SS_OFFLINE=true`, **no network egress** occurs (tests enforce).

---

## Non-Negotiables

- Do **not** alter JSON Schemas or component contracts without explicit instruction.  
- Do **not** store PHI beyond the specified plain text files and `.wav`.  
- Do **not** add analytics, crash reporters, or remote feature flags.

---

## Deliverables Checklist (before you stop)

- [ ] File tree scaffolded per **Repo Map**  
- [ ] Recorder + Transcriber working with latency budget met  
- [ ] Redaction background worker + snapshot endpoint implemented  
- [ ] DAP note generation with **schema enforcement** and text save  
- [ ] Dashboard “Quick Redact → Confirm → Send” gated and working (optional)  
- [ ] Tests passing per **Tests to Implement**  
- [ ] NSIS package builds and runs on Windows 10/11

