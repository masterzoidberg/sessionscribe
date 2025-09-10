from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import uuid
import json
import time
from typing import Dict, List, Any, Optional
from .phi_detector import PHIDetector
from .entity_index import EntityIndex

app = FastAPI(title="SessionScribe PHI Redaction Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3001", "http://localhost:3001"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=False,
)

phi_detector = PHIDetector()
entity_index = EntityIndex()
snapshots: Dict[str, Any] = {}

class TranscriptChunk(BaseModel):
    text: str
    channel: str
    timestamp: float
    t0: float
    t1: float

class RedactionSnapshot(BaseModel):
    snapshot_id: str
    entities: List[Dict[str, Any]]
    preview_diff: str
    original_length: int
    redacted_length: int
    redacted_text: str

@app.post("/redaction/ingest")
async def ingest_chunk(chunk: TranscriptChunk):
    try:
        # Fast regex detection
        fast_entities = phi_detector.detect_fast(chunk.text)
        
        # Add to entity index
        for entity in fast_entities:
            entity_index.add_entity({
                **entity,
                'chunk_id': f"{chunk.timestamp}_{chunk.channel}",
                'context': chunk.text,
                't0': chunk.t0,
                't1': chunk.t1,
                'channel': chunk.channel
            })
        
        return {"status": "processed", "entities_found": len(fast_entities)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/redaction/process-slow")
async def process_slow_detection():
    try:
        # Get all text for slow NER processing
        all_text = entity_index.get_all_text()
        
        if not all_text.strip():
            return {"status": "no_text"}
        
        # Run spaCy NER detection
        slow_entities = await phi_detector.detect_slow(all_text)
        
        # Merge with existing entities
        entity_index.merge_slow_entities(slow_entities)
        
        return {
            "status": "processed", 
            "slow_entities_found": len(slow_entities)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/redaction/snapshot")
async def create_snapshot() -> RedactionSnapshot:
    try:
        snapshot_id = str(uuid.uuid4())
        
        # Get current state
        entities = entity_index.get_all_entities()
        original_text = entity_index.get_all_text()
        
        # Generate redacted version
        redacted_text = phi_detector.apply_redactions(original_text, entities)
        
        # Create preview diff
        preview_diff = generate_preview_diff(original_text, redacted_text, entities[:10])  # First 10 entities
        
        snapshot_data = {
            "snapshot_id": snapshot_id,
            "entities": entities,
            "preview_diff": preview_diff,
            "original_length": len(original_text),
            "redacted_length": len(redacted_text),
            "redacted_text": redacted_text,
            "original_text": original_text,
            "created_at": asyncio.get_event_loop().time()
        }
        
        # Store snapshot
        snapshots[snapshot_id] = snapshot_data
        
        # Clean old snapshots (keep last 12)
        if len(snapshots) > 12:
            oldest_key = min(snapshots.keys(), key=lambda k: snapshots[k]["created_at"])
            del snapshots[oldest_key]
        
        return RedactionSnapshot(**snapshot_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/redaction/snapshot/{snapshot_id}")
async def get_snapshot(snapshot_id: str):
    if snapshot_id not in snapshots:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    return snapshots[snapshot_id]

@app.post("/redaction/apply/{snapshot_id}")
async def apply_redaction(snapshot_id: str, accepted_entities: List[str]):
    if snapshot_id not in snapshots:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    try:
        snapshot = snapshots[snapshot_id]
        
        # Filter entities to only accepted ones
        filtered_entities = [
            entity for entity in snapshot["entities"] 
            if entity["id"] in accepted_entities
        ]
        
        # Apply final redaction
        original_text = snapshot["original_text"]
        final_redacted = phi_detector.apply_redactions(original_text, filtered_entities)
        
        return {
            "status": "applied",
            "redacted_text": final_redacted,
            "entities_applied": len(filtered_entities)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class QuickRedactRequest(BaseModel):
    text: str

@app.post("/redaction/quick")
async def quick_redact(request: QuickRedactRequest):
    """Quick redaction workflow: ingest -> detect -> apply all"""
    try:
        # Clear previous state
        entity_index.clear()
        
        # Ingest text
        chunk = TranscriptChunk(
            text=request.text,
            channel="mixed",
            timestamp=time.time(),
            t0=0.0,
            t1=len(request.text.split()) * 0.5
        )
        
        # Fast regex detection
        fast_entities = phi_detector.detect_fast(chunk.text)
        for entity in fast_entities:
            entity_index.add_entity({
                **entity,
                'chunk_id': f"{chunk.timestamp}_mixed",
                'context': chunk.text,
                't0': chunk.t0,
                't1': chunk.t1,
                'channel': chunk.channel
            })
        
        # Run slow NER detection
        if request.text.strip():
            slow_entities = await phi_detector.detect_slow(request.text)
            entity_index.merge_slow_entities(slow_entities)
        
        # Get all entities and apply redaction
        entities = entity_index.get_all_entities()
        redacted_text = phi_detector.apply_redactions(request.text, entities)
        
        return {
            "status": "success",
            "redacted_text": redacted_text,
            "entities_redacted": len(entities),
            "original_length": len(request.text),
            "redacted_length": len(redacted_text)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def generate_preview_diff(original: str, redacted: str, entities: List[Dict]) -> str:
    lines = []
    lines.append("=== REDACTION PREVIEW ===")
    lines.append(f"Entities found: {len(entities)}")
    lines.append("")
    
    for entity in entities[:5]:  # Show first 5
        lines.append(f"• {entity['label']}: {entity['text']} → [REDACTED]")
    
    if len(entities) > 5:
        lines.append(f"... and {len(entities) - 5} more")
    
    lines.append("")
    lines.append("=== TEXT SAMPLE ===")
    
    # Show a sample of redacted text (first 200 chars)
    sample = redacted[:200]
    if len(redacted) > 200:
        sample += "..."
    lines.append(sample)
    
    return "\n".join(lines)

@app.get("/health")
async def health():
    return {
        "status": "healthy", 
        "service": "redaction",
        "entities_count": entity_index.get_entity_count(),
        "snapshots_count": len(snapshots)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=7032, reload=True)