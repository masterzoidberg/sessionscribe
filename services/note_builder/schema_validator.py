import json
from pathlib import Path
SCHEMA_PATH = Path(__file__).parents[2] / "packages" / "shared" / "schemas" / "note.dap.schema.json"
class SchemaValidator:
    def __init__(self):
        self.dap_schema = self._load_dap_schema()
    def _load_dap_schema(self):
        with open(SCHEMA_PATH, "r", encoding="utf-8-sig") as f:
            return json.load(f)