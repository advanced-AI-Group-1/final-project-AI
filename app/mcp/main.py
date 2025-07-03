"""
MCP (Microservice Communication Protocol) 서버 메인 진입점

이 모듈은 MCP 서버를 실행하는 메인 진입점입니다.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# FastAPI 앱 생성
app = FastAPI(
    title="MCP Server",
    description="Microservice Communication Protocol Server",
    version="1.0.0"
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 운영 환경에서는 특정 도메인으로 제한하는 것이 좋습니다.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
from app.mcp.services import tavily_service
app.include_router(tavily_service.router, prefix="/api/v1/tavily", tags=["tavily"])

@app.get("/")
async def root():
    """기본 엔드포인트"""
    return {
        "service": "MCP Server",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    # 서버 실행 - 기본 포트를 8001로 설정
    uvicorn.run(
        "app.mcp.main:app",
        host=os.getenv("MCP_HOST", "0.0.0.0"),
        port=int(os.getenv("MCP_PORT", "8001")),  # 기본 포트를 8001로 설정
        reload=True,
        log_level="info"
    )
