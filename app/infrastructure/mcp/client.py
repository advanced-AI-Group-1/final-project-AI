"""
MCP (Microservice Communication Protocol) 클라이언트
"""
import httpx
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import os
from urllib.parse import urljoin

class MCPClient:
    """MCP 서버와 통신하기 위한 클라이언트"""
    
    def __init__(self, base_url: str = None):
        """
        MCP 클라이언트 초기화
        
        Args:
            base_url: MCP 서버의 기본 URL (예: http://localhost:8001/api/v1)
        """
        self.base_url = base_url or os.getenv("MCP_BASE_URL")
        if not self.base_url:
            raise ValueError("MCP_BASE_URL 환경 변수가 설정되지 않았습니다.")
            
        self.client = httpx.AsyncClient()
    
    async def close(self):
        """클라이언트 리소스 정리"""
        await self.client.aclose()
    
    async def search_tavily(
        self,
        query: str,
        search_depth: str = "basic",
        max_results: int = 5,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        include_answer: bool = True,
        include_raw_content: bool = True,
        include_images: bool = False,
    ) -> Dict[str, Any]:
        """Tavily 검색 API 호출
        
        Args:
            query: 검색 쿼리
            search_depth: 검색 깊이 ('basic' 또는 'advanced')
            max_results: 최대 결과 수
            include_domains: 검색에 포함할 도메인 목록
            exclude_domains: 검색에서 제외할 도메인 목록
            include_answer: 답변 포함 여부
            include_raw_content: 원본 콘텐츠 포함 여부
            include_images: 이미지 포함 여부
            
        Returns:
            검색 결과 딕셔너리
        """
        # MCP 서버의 Tavily 검색 엔드포인트로 요청 (API 버전 포함)
        # base_url 예: http://localhost:8001/api/v1
        url = urljoin(self.base_url.rstrip('/') + "/", "tavily/search")
        headers = {
            "Content-Type": "application/json"
        }
            
        payload = {
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
            "include_images": include_images,
        }
        
        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains
        
        try:
            response = await self.client.post(
                url,
                json=payload,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_detail = f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
            raise Exception(error_detail) from e
        except Exception as e:
            raise Exception(f"Failed to call MCP Tavily API: {str(e)}") from e

# 전역 MCP 클라이언트 인스턴스
_mcp_client = None

def get_mcp_client() -> MCPClient:
    """전역 MCP 클라이언트 인스턴스를 가져옵니다."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client

async def close_mcp_client():
    """전역 MCP 클라이언트 리소스를 정리합니다."""
    global _mcp_client
    if _mcp_client is not None:
        await _mcp_client.close()
        _mcp_client = None
