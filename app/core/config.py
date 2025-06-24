from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from functools import lru_cache
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Settings(BaseSettings):
    """
    애플리케이션 설정 클래스
    """
    # API 설정
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "금융 AI 분석 API"
    
    # CORS 설정
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # 데이터베이스 설정
    # DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/finance_ai.db")
    
    # OpenAI API 키
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

    # Qdrant API 키
    QDRANT_API_KEY: Optional[str] = os.getenv("QDRANT_API_KEY")
    
    # 벡터 저장소 설정
    VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "data/vector_store")
    
    # LLM 설정
    DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "gpt-4.1-mini")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    
    # RunPod API 키
    RUNPOD_API_KEY: Optional[str] = os.getenv("RUNPOD_API_KEY")

    RUNPOD_ENDPOINT_ID: Optional[str] = os.getenv("RUNPOD_ENDPOINT_ID")

    # VOYAGE API 키
    VOYAGE_API_KEY: Optional[str] = os.getenv("VOYAGE_API_KEY")

    # TAVILY API 키
    TAVILY_API_KEY: Optional[str] = os.getenv("TAVILY_API_KEY")

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    """
    애플리케이션 설정을 반환합니다.
    캐싱을 통해 설정 객체를 재사용합니다.
    """
    return Settings()

# 설정 인스턴스 생성
settings = get_settings()
