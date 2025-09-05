from fastapi import FastAPI, WebSocket
app = FastAPI()

@app.get("/health")
def health(): return {"ok": True}

@app.websocket("/transcribe")
async def transcribe(ws: WebSocket):
    await ws.accept()
    # TODO: receive PCM chunks, run faster-whisper, send partials {channel,text,t0,t1}
    await ws.send_json({"channel":"therapist","text":"stub","t0":0,"t1":1})
    await ws.close()