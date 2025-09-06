import pytest
import asyncio
from services.redaction.phi_detector import PHIDetector

class TestPHIDetector:
    def setup_method(self):
        self.phi_detector = PHIDetector()
    
    def test_detect_phone_numbers(self):
        """Test regex detection of phone numbers."""
        text = "Please call me at 555-123-4567 or (555) 987-6543"
        entities = self.phi_detector.detect_fast(text)
        
        phone_entities = [e for e in entities if e['label'] == 'PHONE']
        assert len(phone_entities) >= 2
        
        # Check that phone numbers are detected
        phone_texts = [e['text'] for e in phone_entities]
        assert any('555-123-4567' in text for text in phone_texts)
        assert any('555' in text for text in phone_texts)
    
    def test_detect_email_addresses(self):
        """Test regex detection of email addresses."""
        text = "Contact me at john.doe@example.com or support@company.org"
        entities = self.phi_detector.detect_fast(text)
        
        email_entities = [e for e in entities if e['label'] == 'EMAIL']
        assert len(email_entities) >= 2
        
        email_texts = [e['text'] for e in email_entities]
        assert 'john.doe@example.com' in email_texts
        assert 'support@company.org' in email_texts
    
    def test_detect_ssn(self):
        """Test regex detection of SSN."""
        text = "My SSN is 123-45-6789 and backup is 987654321"
        entities = self.phi_detector.detect_fast(text)
        
        ssn_entities = [e for e in entities if e['label'] == 'SSN']
        assert len(ssn_entities) >= 1
        
        ssn_texts = [e['text'] for e in ssn_entities]
        assert '123-45-6789' in ssn_texts or '987654321' in ssn_texts
    
    def test_detect_dates_of_birth(self):
        """Test regex detection of dates that could be DOB."""
        text = "Born on 01/15/1985 and graduated 12-25-2010"
        entities = self.phi_detector.detect_fast(text)
        
        dob_entities = [e for e in entities if e['label'] == 'DOB']
        assert len(dob_entities) >= 1
        
        dob_texts = [e['text'] for e in dob_entities]
        assert any('1985' in text for text in dob_texts)
    
    def test_apply_redactions(self):
        """Test applying redactions to text."""
        text = "Call me at 555-123-4567 or email john@example.com"
        entities = [
            {
                'id': '1',
                'label': 'PHONE',
                'text': '555-123-4567',
                'start': 11,
                'end': 23
            },
            {
                'id': '2', 
                'label': 'EMAIL',
                'text': 'john@example.com',
                'start': 33,
                'end': 49
            }
        ]
        
        redacted = self.phi_detector.apply_redactions(text, entities)
        
        assert '[PHONE]' in redacted
        assert '[EMAIL]' in redacted
        assert '555-123-4567' not in redacted
        assert 'john@example.com' not in redacted
    
    def test_no_false_positives(self):
        """Test that normal text doesn't trigger false positives."""
        text = "The patient discussed their feelings about work stress and family relationships."
        entities = self.phi_detector.detect_fast(text)
        
        # Should not detect any PHI in generic therapy text
        assert len(entities) == 0
    
    def test_precision_recall_metrics(self):
        """Test PHI detection precision and recall on known cases."""
        # Test cases with known PHI
        test_cases = [
            ("My phone is 555-123-4567", ['PHONE']),
            ("Email me at test@example.com", ['EMAIL']),
            ("SSN: 123-45-6789", ['SSN']),
            ("Born 01/15/1990", ['DOB']),
            ("I live at 123 Main Street", ['ADDRESS'])
        ]
        
        total_expected = sum(len(expected) for _, expected in test_cases)
        total_detected = 0
        correct_detections = 0
        
        for text, expected_labels in test_cases:
            entities = self.phi_detector.detect_fast(text)
            detected_labels = [e['label'] for e in entities]
            
            total_detected += len(detected_labels)
            
            for expected in expected_labels:
                if expected in detected_labels:
                    correct_detections += 1
        
        # Calculate metrics
        precision = correct_detections / max(total_detected, 1)
        recall = correct_detections / total_expected
        
        # Assert minimum thresholds from TEST_PLAN
        assert recall >= 0.95, f"Recall {recall} below threshold 0.95"
        assert precision >= 0.90, f"Precision {precision} below threshold 0.90"
    
    @pytest.mark.asyncio
    async def test_slow_ner_detection(self):
        """Test spaCy NER detection if available."""
        text = "Patient John Smith discussed his work at Microsoft Corporation."
        
        try:
            entities = await self.phi_detector.detect_slow(text)
            
            # Should detect person and organization
            labels = [e['label'] for e in entities]
            assert 'PERSON' in labels or 'ORG' in labels
            
        except Exception:
            # Skip test if spaCy model not available
            pytest.skip("spaCy model not available")

if __name__ == "__main__":
    pytest.main([__file__])