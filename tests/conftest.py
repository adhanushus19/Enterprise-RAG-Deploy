import pytest
import os
import sys

# Set test environment database URL and OpenAI API key before importing app modules
os.environ["DATABASE_URL"] = "sqlite:///./test_db.db"
os.environ["OPENAI_API_KEY"] = "mock-api-key"

from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Resolve workspace path to locate backend code
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.db.connection import Base, get_db
from app.main import app
from app.config import settings

# Test database using SQLite in-memory
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_db.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    # Remove sqlite file if exists
    if os.path.exists("./test_db.db"):
        try:
            os.remove("./test_db.db")
        except Exception:
            pass

@pytest.fixture
def db() -> Generator:
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db) -> Generator:
    # Override database dependency in FastAPI
    def override_get_db():
        try:
            yield db
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def mock_openai(monkeypatch):
    """
    Mock OpenAI client behaviors to prevent external calls.
    """
    class MockChoices:
        def __init__(self, message_content, parsed_obj=None):
            class Message:
                def __init__(self, content, parsed):
                    self.content = content
                    self.parsed = parsed
            self.message = Message(message_content, parsed_obj)

    class MockCompletion:
        def __init__(self, content, parsed_obj=None):
            self.choices = [MockChoices(content, parsed_obj)]

    class MockChatCompletions:
        def create(self, *args, **kwargs):
            return MockCompletion("This is a mocked answer [1].")
            
        def parse(self, *args, **kwargs):
            # Return appropriate structured response based on schema
            response_format = kwargs.get("response_format")
            if hasattr(response_format, "__name__") and response_format.__name__ == "ExtractedMetadata":
                class ExtractedMetadataMock:
                    author = "Mocked Author"
                    department = "Engineering"
                    creation_date = "2026-06-01"
                    tags = ["mock", "test"]
                    doc_type = "pdf"
                return MockCompletion(None, ExtractedMetadataMock())
                
            elif hasattr(response_format, "__name__") and response_format.__name__ == "VerificationOutput":
                class VerificationOutputMock:
                    passed = True
                    feedback = "Context is sufficient."
                return MockCompletion(None, VerificationOutputMock())
                
            elif hasattr(response_format, "__name__") and response_format.__name__ == "RerankerOutput":
                class ChunkRelevanceMock:
                    def __init__(self, index, score):
                        self.index = index
                        self.relevance_score = score
                        self.reason = "Mock match"
                class RerankerOutputMock:
                    ranked_chunks = [ChunkRelevanceMock(0, 9.5)]
                return MockCompletion(None, RerankerOutputMock())
                
            return MockCompletion("Mock text")

    class MockEmbeddingsData:
        def __init__(self, embedding):
            self.embedding = embedding

    class MockEmbeddingsResponse:
        def __init__(self, embeddings):
            self.data = [MockEmbeddingsData(emb) for emb in embeddings]

    class MockEmbeddings:
        def create(self, *args, **kwargs):
            inputs = kwargs.get("input", [])
            # Return 1536 size dummy floats
            return MockEmbeddingsResponse([[0.1] * 1536 for _ in inputs])

    class MockBeta:
        def __init__(self):
            self.chat = MockChat()

    class MockChat:
        def __init__(self):
            self.completions = MockChatCompletions()

    class MockOpenAI:
        def __init__(self, *args, **kwargs):
            self.chat = MockChat()
            self.embeddings = MockEmbeddings()
            self.beta = MockBeta()

    class MockQdrantCollections:
        def __init__(self):
            self.collections = []

    class MockQdrantHit:
        def __init__(self, point_id, score, payload):
            self.id = point_id
            self.score = score
            self.payload = payload

    class MockQdrantClient:
        def __init__(self, *args, **kwargs):
            pass
        def get_collections(self):
            return MockQdrantCollections()
        def create_collection(self, *args, **kwargs):
            pass
        def upsert(self, *args, **kwargs):
            pass
        def delete(self, *args, **kwargs):
            pass
        def search(self, *args, **kwargs):
            return [
                MockQdrantHit(
                    "mock-v-id", 0.92,
                    {
                        "content": "This is mocked Qdrant chunk text context.",
                        "document_id": "00000000-0000-0000-0000-000000000000",
                        "filename": "mock_policy.pdf",
                        "page_number": 1,
                        "author": "Mock Author",
                        "department": "Engineering",
                        "doc_type": "pdf",
                        "tags": ["test"]
                    }
                )
            ]

    monkeypatch.setattr("app.services.vector_store.QdrantClient", MockQdrantClient)
    monkeypatch.setattr("app.services.document_processor.OpenAI", MockOpenAI)
    monkeypatch.setattr("app.services.vector_store.OpenAI", MockOpenAI)
    monkeypatch.setattr("app.agents.rewriter.OpenAI", MockOpenAI)
    monkeypatch.setattr("app.agents.reranker.OpenAI", MockOpenAI)
    monkeypatch.setattr("app.agents.verification.OpenAI", MockOpenAI)
    monkeypatch.setattr("app.agents.answer.OpenAI", MockOpenAI)
    
    return MockOpenAI
