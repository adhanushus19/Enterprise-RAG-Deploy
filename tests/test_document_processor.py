import pytest
import os
from unittest.mock import MagicMock
from app.services.document_processor import DocumentProcessor

def test_document_processor_initialization(mock_openai):
    processor = DocumentProcessor()
    assert processor.openai_client is not None

def test_parse_pdf(monkeypatch):
    processor = DocumentProcessor()
    
    # Mock pypdf.PdfReader
    class MockPage:
        def extract_text(self):
            return "This is page content text."
            
    class MockReader:
        def __init__(self, path):
            self.pages = [MockPage(), MockPage()]
            
    monkeypatch.setattr("pypdf.PdfReader", MockReader)
    monkeypatch.setattr("os.path.exists", lambda x: True)
    
    chunks = processor.parse_file("dummy.pdf", "pdf")
    
    assert len(chunks) == 2
    assert chunks[0][0] == "This is page content text."
    assert chunks[0][1] == 1
    assert chunks[1][1] == 2

def test_parse_docx(monkeypatch):
    processor = DocumentProcessor()
    
    class MockParagraph:
        def __init__(self, text):
            self.text = text
            
    class MockDoc:
        def __init__(self, path):
            self.paragraphs = [
                MockParagraph("Paragraph 1"),
                MockParagraph("Paragraph 2"),
                MockParagraph("Paragraph 3"),
                MockParagraph("Paragraph 4"),
                MockParagraph("Paragraph 5")
            ]
            
    monkeypatch.setattr("docx.Document", MockDoc)
    monkeypatch.setattr("os.path.exists", lambda x: True)
    
    chunks = processor.parse_file("dummy.docx", "docx")
    
    assert len(chunks) == 2
    assert "Paragraph 1" in chunks[0][0]
    assert chunks[0][1] == 1
    assert "Paragraph 5" in chunks[1][0]
    assert chunks[1][1] == 2

def test_parse_pptx(monkeypatch):
    processor = DocumentProcessor()
    
    class MockShape:
        def __init__(self, text):
            self.text = text
            
    class MockSlide:
        def __init__(self, shapes):
            self.shapes = shapes
            
    class MockPresentation:
        def __init__(self, path):
            self.slides = [
                MockSlide([MockShape("Title Slide"), MockShape("Sub subtitle")]),
                MockSlide([MockShape("Slide 2 Body Content")])
            ]
            
    monkeypatch.setattr("pptx.Presentation", MockPresentation)
    monkeypatch.setattr("os.path.exists", lambda x: True)
    
    chunks = processor.parse_file("dummy.pptx", "pptx")
    
    assert len(chunks) == 2
    assert "Title Slide" in chunks[0][0]
    assert chunks[0][1] == 1
    assert "Slide 2 Body Content" in chunks[1][0]
    assert chunks[1][1] == 2

def test_parse_xlsx(monkeypatch):
    processor = DocumentProcessor()
    
    # Mock pandas read_excel and ExcelFile
    class MockExcelFile:
        def __init__(self, path):
            self.sheet_names = ["Sheet1"]
            
    import pandas as pd
    def mock_read_excel(*args, **kwargs):
        return pd.DataFrame([
            {"Col1": "ValA", "Col2": "ValB"},
            {"Col1": "ValC", "Col2": "ValD"}
        ])
        
    monkeypatch.setattr("pandas.ExcelFile", MockExcelFile)
    monkeypatch.setattr("pandas.read_excel", mock_read_excel)
    monkeypatch.setattr("os.path.exists", lambda x: True)
    
    chunks = processor.parse_file("dummy.xlsx", "xlsx")
    
    assert len(chunks) == 1
    assert "Sheet: Sheet1" in chunks[0][0]
    assert "Col1=ValA" in chunks[0][0]
    assert chunks[0][1] == 1

def test_extract_metadata_llm(mock_openai):
    processor = DocumentProcessor()
    meta = processor.extract_metadata("Sample text content", "test.pdf", "pdf")
    
    assert meta["author"] == "Mocked Author"
    assert meta["department"] == "Engineering"
    assert meta["tags"] == ["mock", "test"]
    assert meta["doc_type"] == "pdf"
