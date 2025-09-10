from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import sys
from typing import Dict, Any, List, Optional
from .note_generator import NoteGenerator
from .schema_validator import SchemaValidator

# Import centralized configuration
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.config import settings

app = FastAPI(title="SessionScribe Note Builder Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3001", "http://localhost:3001"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=False,
)

note_generator = NoteGenerator()
schema_validator = SchemaValidator()

class NoteRequest(BaseModel):
    transcript_redacted: str
    session_type: str = "Individual"
    prompt_version: str = "default"
    custom_prompt: Optional[str] = None

class NoteResponse(BaseModel):
    dap_json: Dict[str, Any]
    validation_status: str  # 'valid', 'invalid', 'repaired'
    validation_errors: List[str]
    note_text: str
    file_path: Optional[str] = None

@app.post("/note/generate")
async def generate_note(request: NoteRequest) -> NoteResponse:
    try:
        # Check if we're in offline mode using centralized config
        if settings.offline_mode:
            # Return placeholder note for offline mode
            dap_json = {
                "session_type": request.session_type,
                "data": "Session data will be available when online mode is enabled.",
                "assessment": "Clinical assessment will be generated when connected to OpenAI API.",
                "plan": "Treatment plan will be formulated when online services are available.",
                "risk_flags": [],
                "followups": []
            }
            
            note_text = format_note_as_text(dap_json)
            
            return NoteResponse(
                dap_json=dap_json,
                validation_status="valid",
                validation_errors=[],
                note_text=note_text
            )
        
        # Online mode - generate with AI
        dap_json = await note_generator.generate_dap_note(
            transcript=request.transcript_redacted,
            session_type=request.session_type,
            prompt_version=request.prompt_version,
            custom_prompt=request.custom_prompt
        )
        
        # Validate against schema
        validation_result = schema_validator.validate_dap_note(dap_json)
        
        if not validation_result["is_valid"]:
            # Attempt repair once
            repaired_json = schema_validator.repair_dap_note(dap_json)
            repaired_validation = schema_validator.validate_dap_note(repaired_json)
            
            if repaired_validation["is_valid"]:
                dap_json = repaired_json
                validation_status = "repaired"
                validation_errors = validation_result["errors"]
            else:
                validation_status = "invalid"
                validation_errors = validation_result["errors"] + repaired_validation["errors"]
        else:
            validation_status = "valid"
            validation_errors = []
        
        # Convert to readable text format
        note_text = format_note_as_text(dap_json)
        
        # Save to file if requested
        file_path = None
        if validation_status in ["valid", "repaired"]:
            file_path = await save_note_to_file(note_text)
        
        return NoteResponse(
            dap_json=dap_json,
            validation_status=validation_status,
            validation_errors=validation_errors,
            note_text=note_text,
            file_path=file_path
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def format_note_as_text(dap_json: Dict[str, Any]) -> str:
    lines = []
    lines.append("=" * 50)
    lines.append("DAP CLINICAL NOTE")
    lines.append("=" * 50)
    lines.append("")
    
    # Session Type
    lines.append(f"Session Type: {dap_json.get('session_type', 'Unknown')}")
    lines.append("")
    
    # Data Section
    lines.append("DATA:")
    lines.append("-" * 20)
    lines.append(dap_json.get('data', ''))
    lines.append("")
    
    # Assessment Section  
    lines.append("ASSESSMENT:")
    lines.append("-" * 20)
    lines.append(dap_json.get('assessment', ''))
    lines.append("")
    
    # Plan Section
    lines.append("PLAN:")
    lines.append("-" * 20) 
    lines.append(dap_json.get('plan', ''))
    lines.append("")
    
    # Risk Flags
    risk_flags = dap_json.get('risk_flags', [])
    if risk_flags:
        lines.append("RISK FLAGS:")
        lines.append("-" * 20)
        for flag in risk_flags:
            lines.append(f"• {flag}")
        lines.append("")
    
    # Follow-ups
    followups = dap_json.get('followups', [])
    if followups:
        lines.append("FOLLOW-UP TASKS:")
        lines.append("-" * 20)
        for task in followups:
            lines.append(f"• {task}")
        lines.append("")
    
    lines.append("=" * 50)
    lines.append("End of Note")
    lines.append("=" * 50)
    
    return "\n".join(lines)

async def save_note_to_file(note_text: str) -> Optional[str]:
    try:
        output_dir = settings.output_dir
        
        os.makedirs(output_dir, exist_ok=True)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"session_{timestamp}_note.txt"
        file_path = os.path.join(output_dir, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(note_text)
        
        return file_path
        
    except Exception as e:
        print(f"Error saving note to file: {e}")
        return None

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "note_builder",
        "offline_mode": settings.offline_mode
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=7034, reload=True)