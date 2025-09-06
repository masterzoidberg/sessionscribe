import os
import json
from typing import Dict, Any, List, Optional
import openai
from openai import OpenAI

class InsightsGenerator:
    def __init__(self):
        self.client = None
        self._setup_openai_client()
        self.model = os.environ.get('SS_NOTE_MODEL', 'gpt-4o-mini')
        self.temperature = 0.1  # Lower temperature for more consistent JSON output
        
    def _setup_openai_client(self):
        api_key = os.environ.get('OPENAI_API_KEY')
        base_url = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        
        if api_key:
            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )
        
    async def generate_insights(
        self, 
        redacted_text: str,
        ask_for: List[str],
        session_type: str = "Individual"
    ) -> Dict[str, Any]:
        if not self.client:
            raise Exception("OpenAI client not configured. Please check OPENAI_API_KEY.")
        
        # Load the insights prompt template
        prompt_template = self._load_insights_template()
        
        # Build the request based on what's being asked for
        ask_for_fields = []
        for field in ask_for:
            if field == "themes":
                ask_for_fields.append("themes")
            elif field == "questions":
                ask_for_fields.append("questions")
            elif field == "missing":
                ask_for_fields.append("missing")
            elif field == "homework":
                ask_for_fields.append("homework")
            elif field == "risk_flags":
                ask_for_fields.append("risk_flags")
        
        # Format the prompt
        formatted_prompt = prompt_template.format(
            session_type=session_type,
            redacted_text=redacted_text[:2000]  # Limit text size
        )
        
        try:
            # Call OpenAI API with JSON mode
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a concise clinical assistant. Respond with JSON only, no prose. Match the insights schema exactly."},
                    {"role": "user", "content": formatted_prompt}
                ],
                temperature=self.temperature,
                max_tokens=800
            )
            
            # Parse the JSON response
            content = response.choices[0].message.content.strip()
            
            # Clean up response (remove markdown formatting if present)
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            
            insights_json = json.loads(content)
            
            # Filter to only requested fields
            filtered_insights = {}
            for field in ask_for_fields:
                if field in insights_json:
                    filtered_insights[field] = insights_json[field]
                else:
                    # Provide empty arrays for missing fields
                    filtered_insights[field] = []
            
            return filtered_insights
            
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse OpenAI response as JSON: {e}")
        except Exception as e:
            raise Exception(f"Error calling OpenAI API: {e}")
    
    def _load_insights_template(self) -> str:
        # Load prompt template from shared prompts directory
        try:
            prompt_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'packages', 'shared', 'prompts', 'Insights.default.md'
            )
            
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        except FileNotFoundError:
            # Fallback to embedded template
            return self._get_default_template()
    
    def _get_default_template(self) -> str:
        return """SYSTEM
You are a concise clinical assistant. Respond with JSON only, no prose.

INPUT
Session Type: {session_type}
Redacted Text (most recent window):
{redacted_text}
Return fields: themes, questions, missing, homework, risk_flags

OUTPUT (JSON only, match schema):
{{
  "themes": [...],
  "questions": [...],
  "missing": [...],
  "homework": [...],
  "risk_flags": [...]
}}"""