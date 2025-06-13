from typing import Dict, Any, Optional
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import AsyncEngine
from contextlib import asynccontextmanager

# SQLAlchemy 모델 기본 클래스
Base = declarative_base()

class DatabaseConnection:
    """
    데이터베이스 연결 및 세션 관리를 위한 클래스
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # 환경 변수에서 데이터베이스 URL 가져오기
        self.db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/finance_ai.db")
        
        # 비동기 엔진 생성
        self.engine = create_async_engine(
            self.db_url,
            echo=True,  # SQL 쿼리 로깅 활성화
            future=True
        )
        
        # 세션 팩토리 생성
        self.async_session_factory = sessionmaker(
            self.engine,
            expire_on_commit=False,
            class_=AsyncSession
        )
        
        self._initialized = True
    
    @asynccontextmanager
    async def get_session(self):
        """
        비동기 데이터베이스 세션을 제공하는 컨텍스트 매니저
        """
        session = self.async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()
            
    async def create_tables(self):
        """
        모든 정의된 테이블을 데이터베이스에 생성합니다.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
    async def drop_tables(self):
        """
        모든 정의된 테이블을 데이터베이스에서 삭제합니다.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            
# 데이터베이스 연결 인스턴스 생성
db = DatabaseConnection()
