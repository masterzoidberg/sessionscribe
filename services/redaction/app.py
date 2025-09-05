from fastapi import FastAPI
from pydantic import BaseModel
from uuid import uuid4

app = FastAPI()
_latest_text = ""
_latest_snapshot = {"id": None, "text": ""}

class Ingest(BaseModel):
    text: str

@app.post("/redaction/ingest_chunk")
def ingest(c: Ingest):
    global _latest_text
    _latest_text += c.text
    return {"len": len(_latest_text)}

@app.get("/redaction/snapshot")
def snapshot():
    global _latest_snapshot
    sid = str(uuid4())
    # TODO: apply regex/NER redaction into snap_text
    snap_text = _latest_text
    _latest_snapshot = {"id": sid, "text": snap_text}
    return {"snapshot_id": sid, "original_len": len(_latest_text), "redacted_len": len(snap_text), "entities": [], "preview_diff": ""}

@app.post("/redaction/apply_edits")
def apply_edits():
    # TODO: accept replacements and finalize
    return {"ok": True}