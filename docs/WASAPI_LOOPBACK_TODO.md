# WASAPI Loopback Implementation - Tracked Feature

**Status**: TODO - Not implemented in Round 2  
**Priority**: Low  
**Milestone**: Future Feature Release  

## Overview

Currently, SessionScribe uses simulated audio capture. Real WASAPI loopback capture needs to be implemented for production-quality audio recording from system output devices.

## Current State

- ✅ Audio interface stubs exist in `services/asr/audio_wasapi.py`
- ✅ Mock capture methods return silence
- ✅ Device enumeration partially implemented
- ❌ Real WASAPI loopback capture not implemented

## Implementation Plan

### Phase 1: WASAPI Foundation
- [ ] Integrate `pycaw` for Windows Audio Session API access
- [ ] Implement `pywin32` bindings for low-level audio interfaces  
- [ ] Replace silence generation with real device binding

### Phase 2: Loopback Capture
- [ ] Bind to default render device in loopback mode
- [ ] Implement real-time PCM audio streaming
- [ ] Add proper buffer management and timing

### Phase 3: Multi-Device Support
- [ ] Support multiple input/output device selection
- [ ] Add device hot-plugging detection
- [ ] Implement exclusive mode for low-latency capture

## Code Locations

**Primary Implementation File:**
```
services/asr/audio_wasapi.py:95-120
```

**Current Stub (to be replaced):**
```python
def start_loopback_capture(self):
    # TODO: Implement real WASAPI loopback
    return self._generate_silence()
```

## Dependencies Required

```python
# Add to services/asr/requirements.txt
pycaw>=20240210.1
pywin32>=306
```

## Acceptance Criteria

- [ ] Real audio captured from system speakers/output
- [ ] Low-latency streaming (< 100ms buffer)
- [ ] Stable capture without dropouts
- [ ] Device selection works reliably
- [ ] Integration tests pass with real audio

## Related Issues

- #TODO-001: WASAPI Loopback Implementation
- #TODO-002: Audio Device Management
- #TODO-003: Low-Latency Audio Pipeline

## Timeline

**Estimated effort**: 1-2 weeks  
**Blocked by**: Round 2 completion  
**Next milestone**: Q1 2025

---

*This feature was deliberately excluded from Round 2 fixes to focus on stability and security improvements. It will be addressed in a future feature development cycle.*