import re
import asyncio
import spacy
from typing import List, Dict, Any
import uuid
from concurrent.futures import ThreadPoolExecutor

class PHIDetector:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.nlp = None
        self._load_spacy_model()
        
        # PHI patterns (regex-based fast detection)
        self.phi_patterns = {
            'PHONE': [
                r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
                r'\b\d{3}-\d{3}-\d{4}\b',
                r'\b\d{10}\b'
            ],
            'EMAIL': [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ],
            'SSN': [
                r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b',
                r'\b\d{9}\b'
            ],
            'DOB': [
                r'\b\d{1,2}[/\-]\d{1,2}[/\-]\d{4}\b',
                r'\b\d{4}[/\-]\d{1,2}[/\-]\d{1,2}\b'
            ],
            'AGE': [
                r'\b(?:age|aged?)\s+(\d{1,3})\b',
                r'\b(\d{1,3})\s*(?:years?\s*old|y\.?o\.?)\b'
            ],
            'ADDRESS': [
                r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Court|Ct)\b',
                r'\b\d{5}(?:-\d{4})?\b'  # ZIP codes
            ],
            'MRN': [
                r'\b(?:MRN|mrn|medical\s+record)\s*:?\s*([A-Z0-9]+)\b',
                r'\b[A-Z]{2,}\d{4,}\b'
            ]
        }

    def _load_spacy_model(self):
        try:
            # Try to load English model
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            try:
                # Try alternative loading method
                import en_core_web_sm
                self.nlp = en_core_web_sm.load()
            except (ImportError, OSError):
                print("Warning: spaCy English model not found. Run: python -m spacy download en_core_web_sm")
                self.nlp = None

    def detect_fast(self, text: str) -> List[Dict[str, Any]]:
        entities = []
        
        for label, patterns in self.phi_patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    entity = {
                        'id': str(uuid.uuid4()),
                        'label': label,
                        'text': match.group(0),
                        'start': match.start(),
                        'end': match.end(),
                        'confidence': 0.8,  # Regex confidence
                        'method': 'regex'
                    }
                    entities.append(entity)
        
        return entities

    async def detect_slow(self, text: str) -> List[Dict[str, Any]]:
        if not self.nlp:
            return []
        
        # Run spaCy NER in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        doc = await loop.run_in_executor(self.executor, self.nlp, text)
        
        entities = []
        for ent in doc.ents:
            # Map spaCy labels to our PHI categories
            phi_label = self._map_spacy_label(ent.label_)
            if phi_label:
                entity = {
                    'id': str(uuid.uuid4()),
                    'label': phi_label,
                    'text': ent.text,
                    'start': ent.start_char,
                    'end': ent.end_char,
                    'confidence': 0.9,  # spaCy confidence
                    'method': 'ner',
                    'spacy_label': ent.label_
                }
                entities.append(entity)
        
        return entities

    def _map_spacy_label(self, spacy_label: str) -> str:
        mapping = {
            'PERSON': 'PERSON',
            'ORG': 'ORG', 
            'GPE': 'ADDRESS',  # Geopolitical entity
            'DATE': 'DOB',
            'TIME': 'DOB',
            'CARDINAL': 'AGE',  # Numbers that could be ages
            'ORDINAL': 'AGE'
        }
        return mapping.get(spacy_label)

    def apply_redactions(self, text: str, entities: List[Dict[str, Any]]) -> str:
        if not entities:
            return text
        
        # Sort entities by start position (reverse order for safe replacement)
        sorted_entities = sorted(entities, key=lambda x: x['start'], reverse=True)
        
        redacted_text = text
        for entity in sorted_entities:
            # Replace with redaction marker
            redaction = f"[{entity['label']}]"
            start, end = entity['start'], entity['end']
            
            # Bounds checking
            if start >= 0 and end <= len(redacted_text) and start < end:
                redacted_text = redacted_text[:start] + redaction + redacted_text[end:]
        
        return redacted_text

    def get_entity_categories(self) -> List[str]:
        return list(self.phi_patterns.keys()) + ['PERSON', 'ORG']