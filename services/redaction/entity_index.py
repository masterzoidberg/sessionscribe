from typing import Dict, List, Any, Set
import time

class EntityIndex:
    def __init__(self):
        self.entities: Dict[str, Dict[str, Any]] = {}
        self.text_chunks: List[Dict[str, Any]] = []
        self.entity_precedence = {
            'SSN': 10,
            'MRN': 9,
            'PHONE': 8,
            'EMAIL': 7,
            'DOB': 6,
            'PERSON': 5,
            'ADDRESS': 4,
            'AGE': 3,
            'ORG': 2,
            'HANDLE': 1
        }

    def add_entity(self, entity: Dict[str, Any]):
        entity_id = entity['id']
        
        # Add timestamp
        entity['created_at'] = time.time()
        
        # Check for duplicates and merge
        existing_id = self._find_duplicate(entity)
        if existing_id:
            self._merge_entities(existing_id, entity)
        else:
            self.entities[entity_id] = entity

    def _find_duplicate(self, entity: Dict[str, Any]) -> str:
        text_lower = entity['text'].lower().strip()
        label = entity['label']
        
        for existing_id, existing_entity in self.entities.items():
            if (existing_entity['label'] == label and 
                existing_entity['text'].lower().strip() == text_lower):
                return existing_id
        
        return None

    def _merge_entities(self, existing_id: str, new_entity: Dict[str, Any]):
        existing = self.entities[existing_id]
        
        # Update confidence if new method has higher precedence
        if self._get_method_precedence(new_entity['method']) > self._get_method_precedence(existing['method']):
            existing['confidence'] = max(existing['confidence'], new_entity['confidence'])
            existing['method'] = new_entity['method']
        
        # Add context information
        if 'contexts' not in existing:
            existing['contexts'] = []
        
        existing['contexts'].append({
            'chunk_id': new_entity.get('chunk_id'),
            'context': new_entity.get('context', ''),
            'channel': new_entity.get('channel'),
            't0': new_entity.get('t0'),
            't1': new_entity.get('t1')
        })

    def _get_method_precedence(self, method: str) -> int:
        precedence = {'ner': 2, 'regex': 1}
        return precedence.get(method, 0)

    def merge_slow_entities(self, slow_entities: List[Dict[str, Any]]):
        for entity in slow_entities:
            self.add_entity(entity)

    def get_all_entities(self) -> List[Dict[str, Any]]:
        entities_list = list(self.entities.values())
        
        # Sort by precedence, then by confidence
        entities_list.sort(key=lambda x: (
            -self.entity_precedence.get(x['label'], 0),
            -x['confidence']
        ))
        
        return entities_list

    def get_entity_count(self) -> int:
        return len(self.entities)

    def add_text_chunk(self, chunk: Dict[str, Any]):
        self.text_chunks.append(chunk)

    def get_all_text(self) -> str:
        # Reconstruct text from chunks in chronological order
        sorted_chunks = sorted(self.text_chunks, key=lambda x: x.get('timestamp', 0))
        return ' '.join(chunk.get('text', '') for chunk in sorted_chunks)

    def get_entities_by_label(self, label: str) -> List[Dict[str, Any]]:
        return [entity for entity in self.entities.values() if entity['label'] == label]

    def remove_entity(self, entity_id: str) -> bool:
        if entity_id in self.entities:
            del self.entities[entity_id]
            return True
        return False

    def update_entity_status(self, entity_id: str, accepted: bool):
        if entity_id in self.entities:
            self.entities[entity_id]['accepted'] = accepted
            return True
        return False

    def get_accepted_entities(self) -> List[Dict[str, Any]]:
        return [
            entity for entity in self.entities.values() 
            if entity.get('accepted', True)
        ]

    def clear(self):
        self.entities.clear()
        self.text_chunks.clear()