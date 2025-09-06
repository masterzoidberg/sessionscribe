from fastapi.testclient import TestClient
from services.redaction.app import app

def test_snapshot_empty_returns_schema():
    client = TestClient(app)
    r = client.get("/redaction/snapshot")
    assert r.status_code == 200
    data = r.json()
    assert "snapshot_id" in data
    assert "original_len" in data
    assert "redacted_len" in data
    assert "entities" in data
    assert "preview_diff" in data

def test_ingest_then_snapshot_len_increases():
    client = TestClient(app)
    before = client.get("/redaction/snapshot").json()["original_len"]
    client.post("/redaction/ingest_chunk", json={"text": "Client name is John Doe. Phone 555-123-4567."})
    after = client.get("/redaction/snapshot").json()["original_len"]
    assert after > before