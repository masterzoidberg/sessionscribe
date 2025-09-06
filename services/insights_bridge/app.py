from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
from typing import Dict, Any, List, Optional
from .insights_generator import InsightsGenerator
from .schema_validator import InsightsSchemaValidator

app = FastAPI(title="SessionScribe Insights Bridge Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

insights_generator = InsightsGenerator()
schema_validator = InsightsSchemaValidator()

class InsightsRequest(BaseModel):
    snapshot_id: str
    ask_for: List[str]  # ["themes", "questions", "missing", "homework", "risk_flags"]

class InsightsResponse(BaseModel):
    themes: Optional[List[str]] = None
    questions: Optional[List[str]] = None
    missing: Optional[List[str]] = None
    homework: Optional[List[str]] = None
    risk_flags: Optional[List[str]] = None

@app.post("/insights/send")
async def send_for_insights(request: InsightsRequest) -> InsightsResponse:
    # Check gates first
    offline_mode = os.environ.get('SS_OFFLINE', 'true').lower() == 'true'
    redact_before_send = os.environ.get('SS_REDACT_BEFORE_SEND', 'true').lower() == 'true'
    
    if offline_mode:
        raise HTTPException(status_code=403, detail="Insights disabled in offline mode")
    
    if not redact_before_send:
        raise HTTPException(status_code=403, detail="Redaction required before sending to insights")
    
    try:
        # Get redacted text from snapshot
        redacted_text = await get_redacted_text_from_snapshot(request.snapshot_id)
        
        if not redacted_text:
            raise HTTPException(status_code=404, detail="Snapshot not found or contains no redacted text")
        
        # Generate insights using OpenAI
        insights_json = await insights_generator.generate_insights(
            redacted_text=redacted_text,
            ask_for=request.ask_for
        )
        
        # Validate against schema
        validation_result = schema_validator.validate_insights(insights_json)
        
        if not validation_result["is_valid"]:
            # Drop invalid fields and return what we can
            insights_json = schema_validator.clean_insights(insights_json)
        
        # Filter response to only requested fields
        filtered_response = {}
        for field in request.ask_for:
            if field in insights_json:
                filtered_response[field] = insights_json[field]
        
        return InsightsResponse(**filtered_response)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def get_redacted_text_from_snapshot(snapshot_id: str) -> Optional[str]:
    """Fetch redacted text from the redaction service snapshot."""
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://localhost:7032/redaction/snapshot/{snapshot_id}")
            
            if response.status_code == 200:
                snapshot_data = response.json()
                return snapshot_data.get("redacted_text", "")
            else:
                return None
                
    except Exception as e:
        print(f"Error fetching snapshot: {e}")
        return None

@app.get("/insights/status")
async def get_insights_status():
    """Return the current status of insights service gates."""
    offline_mode = os.environ.get('SS_OFFLINE', 'true').lower() == 'true'
    redact_before_send = os.environ.get('SS_REDACT_BEFORE_SEND', 'true').lower() == 'true'
    
    return {
        "available": not offline_mode and redact_before_send,
        "offline_mode": offline_mode,
        "redact_before_send": redact_before_send,
        "provider": os.environ.get('SS_DASHBOARD_PROVIDER', 'openai_api')
    }

@app.get("/health")
async def health():
    offline_mode = os.environ.get('SS_OFFLINE', 'true').lower() == 'true'
    
    return {
        "status": "healthy",
        "service": "insights_bridge",
        "offline_mode": offline_mode,
        "provider": os.environ.get('SS_DASHBOARD_PROVIDER', 'openai_api')
    }