import json
from pathlib import Path
SCHEMA_PATH = Path(__file__).parents[2] / "packages" / "shared" / "schemas" / "insights.schema.json"
class InsightsSchemaValidator:
    def __init__(self):
        self.insights_schema = self._load_insights_schema()
    def _load_insights_schema(self):
        with open(SCHEMA_PATH, "r", encoding="utf-8-sig") as f:
            return json.load(f)