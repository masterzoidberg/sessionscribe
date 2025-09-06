import pytest
import json
from services.note_builder.schema_validator import SchemaValidator

class TestSchemaValidator:
    def setup_method(self):
        self.validator = SchemaValidator()
    
    def test_valid_dap_note(self):
        """Test validation of a valid DAP note."""
        valid_note = {
            "session_type": "Individual",
            "data": "Client presented with symptoms of anxiety and discussed coping strategies.",
            "assessment": "Client shows progress in managing anxiety with improved coping mechanisms.",
            "plan": "Continue weekly sessions focusing on cognitive behavioral techniques.",
            "risk_flags": [],
            "followups": ["Review homework assignment", "Schedule follow-up in one week"]
        }
        
        result = self.validator.validate_dap_note(valid_note)
        
        assert result["is_valid"] == True
        assert len(result["errors"]) == 0
    
    def test_invalid_dap_note_missing_required(self):
        """Test validation failure for missing required fields."""
        invalid_note = {
            "session_type": "Individual",
            "data": "Some data"
            # Missing required 'assessment' and 'plan' fields
        }
        
        result = self.validator.validate_dap_note(invalid_note)
        
        assert result["is_valid"] == False
        assert len(result["errors"]) > 0
        assert any("required" in error.lower() for error in result["errors"])
    
    def test_invalid_session_type(self):
        """Test validation failure for invalid session type."""
        invalid_note = {
            "session_type": "InvalidType",
            "data": "Client presented with symptoms of anxiety and discussed various topics.",
            "assessment": "Client shows some progress in managing their concerns.",
            "plan": "Continue sessions and monitor progress over time."
        }
        
        result = self.validator.validate_dap_note(invalid_note)
        
        assert result["is_valid"] == False
    
    def test_field_length_validation(self):
        """Test validation of field length constraints."""
        # Test minimum length violation
        short_note = {
            "session_type": "Individual",
            "data": "Short",  # Too short
            "assessment": "Short",  # Too short  
            "plan": "Short"  # Too short
        }
        
        result = self.validator.validate_dap_note(short_note)
        assert result["is_valid"] == False
        
        # Test maximum length violation
        long_text = "x" * 3001  # Exceeds 3000 character limit
        long_note = {
            "session_type": "Individual",
            "data": long_text,
            "assessment": "This assessment meets minimum length requirements for validation.",
            "plan": "This plan meets minimum length requirements for validation testing."
        }
        
        result = self.validator.validate_dap_note(long_note)
        assert result["is_valid"] == False
    
    def test_repair_dap_note_missing_fields(self):
        """Test repairing a DAP note with missing required fields."""
        incomplete_note = {
            "session_type": "Individual"
            # Missing all required fields
        }
        
        repaired = self.validator.repair_dap_note(incomplete_note)
        validation = self.validator.validate_dap_note(repaired)
        
        assert validation["is_valid"] == True
        assert len(repaired["data"]) >= 10
        assert len(repaired["assessment"]) >= 10
        assert len(repaired["plan"]) >= 10
    
    def test_repair_dap_note_invalid_session_type(self):
        """Test repairing a DAP note with invalid session type."""
        note_with_invalid_type = {
            "session_type": "InvalidType",
            "data": "Client discussed their recent experiences and challenges in daily life.",
            "assessment": "Client demonstrates awareness of their situation and willingness to engage.",
            "plan": "Continue therapeutic interventions and monitor progress in upcoming sessions."
        }
        
        repaired = self.validator.repair_dap_note(note_with_invalid_type)
        
        assert repaired["session_type"] == "Individual"
        
        validation = self.validator.validate_dap_note(repaired)
        assert validation["is_valid"] == True
    
    def test_repair_dap_note_too_long(self):
        """Test repairing a DAP note with fields that are too long."""
        long_text = "x" * 3001  # Exceeds limit
        
        note_too_long = {
            "session_type": "Individual",
            "data": long_text,
            "assessment": long_text,
            "plan": long_text
        }
        
        repaired = self.validator.repair_dap_note(note_too_long)
        
        assert len(repaired["data"]) <= 3000
        assert len(repaired["assessment"]) <= 3000
        assert len(repaired["plan"]) <= 3000
        
        validation = self.validator.validate_dap_note(repaired)
        assert validation["is_valid"] == True
    
    def test_repair_removes_additional_properties(self):
        """Test that repair removes properties not in schema."""
        note_with_extra = {
            "session_type": "Individual",
            "data": "Client presented with symptoms and discussed various coping strategies.",
            "assessment": "Client shows good insight and engagement with therapeutic process.",
            "plan": "Continue weekly sessions with focus on skill building and practice.",
            "extra_field": "This should be removed",
            "another_extra": 123
        }
        
        repaired = self.validator.repair_dap_note(note_with_extra)
        
        assert "extra_field" not in repaired
        assert "another_extra" not in repaired
        
        validation = self.validator.validate_dap_note(repaired)
        assert validation["is_valid"] == True
    
    def test_array_fields_validation(self):
        """Test validation of array fields (risk_flags, followups)."""
        note_with_arrays = {
            "session_type": "Individual",
            "data": "Client discussed ongoing challenges and recent progress in therapy.",
            "assessment": "Client demonstrates improved coping skills and emotional regulation.", 
            "plan": "Continue current treatment approach with weekly sessions and skill practice.",
            "risk_flags": ["High anxiety levels", "Social isolation"],
            "followups": ["Complete anxiety questionnaire", "Practice relaxation techniques"]
        }
        
        result = self.validator.validate_dap_note(note_with_arrays)
        assert result["is_valid"] == True
        
        # Test with invalid array types
        note_invalid_arrays = note_with_arrays.copy()
        note_invalid_arrays["risk_flags"] = "not an array"
        note_invalid_arrays["followups"] = 123
        
        result = self.validator.validate_dap_note(note_invalid_arrays)
        assert result["is_valid"] == False
    
    def test_100_percent_json_validity(self):
        """Test that all repaired notes achieve 100% JSON validity."""
        # Test cases that should be repairable
        test_cases = [
            {},  # Empty
            {"session_type": "Invalid"},  # Invalid type
            {"data": "short"},  # Too short
            {"session_type": "Individual", "data": "x" * 3001},  # Too long
            {"extra": "field", "session_type": "Individual"}  # Extra fields
        ]
        
        for i, test_case in enumerate(test_cases):
            repaired = self.validator.repair_dap_note(test_case)
            validation = self.validator.validate_dap_note(repaired)
            
            assert validation["is_valid"] == True, f"Test case {i} failed to repair to valid JSON"
    
    def test_get_schema_requirements(self):
        """Test retrieval of schema requirements for UI display."""
        requirements = self.validator.get_schema_requirements()
        
        assert "required_fields" in requirements
        assert "field_limits" in requirements
        assert "data" in requirements["required_fields"]
        assert "assessment" in requirements["required_fields"]
        assert "plan" in requirements["required_fields"]

if __name__ == "__main__":
    pytest.main([__file__])