from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class SendInsights(BaseModel):
    snapshot_id: str
    ask_for: list[str]

@app.post("/insights/send")
def send_insights(req: SendInsights):
    # TODO: resolve snapshot by id, call OpenAI with JSON-only prompt, validate against insights schema
    return {"themes": ["stub"], "questions": ["What changed since last week?"], "missing": [], "homework": [], "risk_flags": []}