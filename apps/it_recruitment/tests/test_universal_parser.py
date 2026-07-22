import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from apps.it_recruitment.services.universal_resume_parser import UniversalResumeParserService
from apps.it_recruitment.services.semantic_resume_analyzer import SemanticResumeAnalyzer
from apps.it_recruitment.services.resume_ocr_service import ResumeOCRService
from apps.documents.models import StoredFile

def test_semantic_analyzer_basic():
    analyzer = SemanticResumeAnalyzer()
    raw_text = """
    Praveen Kumar
    praveen@gmail.com
    9876543210
    
    Professional Summary
    Highly motivated Python developer with 5 years of experience.
    
    Work Experience
    Software Engineer at Tech Corp
    Developed Django apps.
    
    Skills
    Python, Django, React, AWS
    """
    result = analyzer.analyze(raw_text)
    
    assert result["name"] == "Praveen Kumar"
    assert result["email"] == "praveen@gmail.com"
    assert result["phone"] == "9876543210"
    assert "Python" in result["skills"]
    assert "Django" in result["skills"]
    assert len(result["summary"]) > 0
    assert "Highly motivated Python developer with 5 years of experience." in result["summary"]
    assert len(result["experience"]) > 0

@patch("apps.it_recruitment.services.resume_ocr_service.ResumeOCRService.extract_text")
@patch("apps.documents.services.storage_service.StorageService.get_absolute_path")
def test_universal_parser_routes_image_to_ocr(mock_get_path, mock_ocr):
    mock_get_path.return_value = "/tmp/fake_resume.png"
    mock_ocr.return_value = "Extracted OCR text"
    
    stored = MagicMock(spec=StoredFile)
    stored.original_filename = "fake_resume.png"
    
    # We patch Path.exists so it doesn't fail the file check
    with patch.object(Path, 'exists', return_value=True):
        service = UniversalResumeParserService()
        result = service._extract_text(stored)
        
        assert result == "Extracted OCR text"
        mock_ocr.assert_called_once()
