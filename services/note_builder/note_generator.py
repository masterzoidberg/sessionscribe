import os
import json
from typing import Dict, Any, Optional
import openai
from openai import OpenAI

class NoteGenerator:
    def __init__(self):
        self.client = None
        self._setup_openai_client()
        self.model = os.environ.get('SS_NOTE_MODEL', 'gpt-4o-mini')
        self.temperature = float(os.environ.get('SS_NOTE_TEMPERATURE', '0.2'))
        
    def _setup_openai_client(self):
        api_key = os.environ.get('OPENAI_API_KEY')
        base_url = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        
        if api_key:
            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )
        
    async def generate_dap_note(
        self, 
        transcript: str, 
        session_type: str = "Individual",
        prompt_version: str = "default",
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self.client:
            raise Exception("OpenAI client not configured. Please check OPENAI_API_KEY.")
        
        # Load the appropriate prompt template
        if custom_prompt:
            prompt_template = custom_prompt
        else:
            prompt_template = self._load_prompt_template(prompt_version)
        
        # Format the prompt with session data
        formatted_prompt = prompt_template.format(
            session_type=session_type,
            transcript_redacted=transcript[:4000]  # Truncate to stay within limits
        )
        
        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a clinical note writer. Return only valid JSON that matches the DAP schema. No additional text."},
                    {"role": "user", "content": formatted_prompt}
                ],
                temperature=self.temperature,
                max_tokens=1500
            )
            
            # Parse the JSON response
            content = response.choices[0].message.content.strip()
            
            # Clean up response (remove markdown formatting if present)
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            
            dap_json = json.loads(content)
            
            # Ensure required fields are present
            dap_json.setdefault('session_type', session_type)
            dap_json.setdefault('risk_flags', [])
            dap_json.setdefault('followups', [])
            
            return dap_json
            
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse OpenAI response as JSON: {e}")
        except Exception as e:
            raise Exception(f"Error calling OpenAI API: {e}")
    
    def _load_prompt_template(self, version: str = "default") -> str:
        # Load prompt template from shared prompts directory
        try:
            prompt_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'packages', 'shared', 'prompts', 'DAP.default.md'
            )
            
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        except FileNotFoundError:
            # Fallback to embedded template
            return self._get_default_template()
    
    def _get_default_template(self) -> str:
        return """SYSTEM
You write concise clinical notes for a licensed psychotherapist. Use short, clear sentences. No disclaimers.

CONTEXT
Session Type: {session_type}
Redacted Transcript:
{transcript_redacted}

OUTPUT
Return ONLY valid JSON for the DAP schema with keys:
session_type, data, assessment, plan, risk_flags, followups

Constraints:
- Neutral clinical language.
- No PHI or identifiers.
- 250–600 words across data/assessment/plan."""