from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from app.domain.financial_data.service import FinancialDataService

router = APIRouter()

class PromptRequest(BaseModel):
    prompt: str
    top_k: int = 5  # 유사도 기준으로 상위 몇 개의 기업 데이터를 반환할지

class FinancialDataResponse(BaseModel):
    company_name: str
    similarity_score: float
    financial_statements: Dict[str, Any]

@router.post("/search", response_model=List[FinancialDataResponse])
async def search_financial_data(request: PromptRequest):
    """
    프롬프트를 받아 RAG를 통해 유사도가 높은 기업의 재무제표 데이터를 반환합니다.
    """
    try:
        service = FinancialDataService()
        results = await service.search_similar_financial_data(request.prompt, request.top_k)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"재무제표 데이터 검색 중 오류 발생: {str(e)}")
