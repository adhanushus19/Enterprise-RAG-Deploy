import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgrespassword@localhost:5432/knowledge_assistant",
        description="SQLAlchemy database connection string"
    )
    QDRANT_HOST: str = Field(default="localhost", description="Qdrant service host name")
    QDRANT_PORT: int = Field(default=6333, description="Qdrant HTTP port")
    OPENAI_API_KEY: str = Field(default="", description="OpenAI api key for embeddings and generation")
    API_KEY: str = Field(default="enterprise-secret-key-123", description="API Secret key for header authorization")
    ENVIRONMENT: str = Field(default="development", description="Application runtime environment")
    UPLOAD_DIR: str = Field(default="uploads", description="Directory where files are stored")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
