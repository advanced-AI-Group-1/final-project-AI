"""
Tavily 검색 서비스를 위한 MCP 서버 모듈
"""
import os
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from tavily import TavilyClient

from fastapi import APIRouter

# FastAPI 라우터 생성
router = APIRouter()

# 환경 변수에서 API 키 로드
tavily_api_key = os.getenv("TAVILY_API_KEY")
if not tavily_api_key:
    raise ValueError("TAVILY_API_KEY 환경 변수가 설정되지 않았습니다.")

tavily_client = TavilyClient(api_key=tavily_api_key)

class SearchRequest(BaseModel):
    query: str
    search_depth: str = "basic"  # 'basic' 또는 'advanced'
    max_results: int = 5
    include_domains: Optional[list[str]] = None
    exclude_domains: Optional[list[str]] = None
    include_answer: bool = True
    include_raw_content: bool = True
    include_images: bool = False

class SearchResponse(BaseModel):
    results: list[Dict[str, Any]]
    answer: Optional[str] = None
    images: Optional[list[str]] = None

@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    x_api_key: str = Header(None, description="API 키 (선택사항)"),
):
    """
    Tavily을 사용해 검색을 수행합니다.
    API 키 검증 없이 사용 가능합니다.
    """
    try:
        # API 키 검증 없음 (모든 요청 허용)
        
        # 검색 파라미터 구성
        search_kwargs = {
            "query": request.query,
            "search_depth": request.search_depth,
            "include_answer": request.include_answer,
            "include_raw_content": request.include_raw_content,
            "include_images": request.include_images,
            "max_results": request.max_results,
        }
        
        if request.include_domains:
            search_kwargs["include_domains"] = request.include_domains
        if request.exclude_domains:
            search_kwargs["exclude_domains"] = request.exclude_domains
        
        # Tavily 검색 실행
        response = tavily_client.search(**search_kwargs)
        
        return SearchResponse(
            results=response.get("results", []),
            answer=response.get("answer"),
            images=response.get("images")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
