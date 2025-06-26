from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

from app.domain.financial_data.service import FinancialDataService

# 로깅 설정
logger = logging.getLogger(__name__)

router = APIRouter()


class PromptRequest(BaseModel):
  prompt: str
  top_k: int = 8  # 유사도 기준으로 상위 몇 개의 기업 데이터를 반환할지


class FilterRequest(BaseModel):
  industry: Optional[str] = None
  min_revenue: Optional[float] = None
  max_debt_ratio: Optional[float] = None
  top_k: int = 8


class FinancialDataResponse(BaseModel):
  company_name: str
  similarity_score: float
  financial_statements: Dict[str, Any]


class InitVectorStoreResponse(BaseModel):
  status: str
  message: str


@router.post("/initialize-vector-store", response_model=InitVectorStoreResponse)
async def initialize_vector_store():
  """
    벡터 스토어를 초기화하고 CSV 데이터를 로드합니다.
    """
  try:
    logger.info("벡터 스토어 초기화 API 호출")
    service = FinancialDataService()
    # 동기 함수로 직접 호출
    success = service.initialize_vector_store()

    if success:
      return {"status": "success", "message": "벡터 스토어 초기화가 완료되었습니다."}
    else:
      return {"status": "error", "message": "벡터 스토어 초기화 중 오류가 발생했습니다."}
  except Exception as e:
    logger.error(f"벡터 스토어 초기화 중 예외 발생: {str(e)}")
    raise HTTPException(status_code=500, detail=f"벡터 스토어 초기화 중 오류 발생: {str(e)}")


@router.post("/search", response_model=List[FinancialDataResponse])
async def search_financial_data(request: PromptRequest):
  """
    프롬프트를 받아 RAG를 통해 유사도가 높은 기업의 재무제표 데이터를 반환합니다.
    """
  try:
    logger.info(f"유사도 검색 API 호출: {request.prompt}")
    service = FinancialDataService()
    results = await service.search_similar_financial_data(request.prompt, request.top_k)
    return results
  except Exception as e:
    logger.error(f"재무제표 데이터 검색 중 오류 발생: {str(e)}")
    raise HTTPException(status_code=500, detail=f"재무제표 데이터 검색 중 오류 발생: {str(e)}")


@router.post("/filter", response_model=List[FinancialDataResponse])
async def filter_financial_data(request: FilterRequest):
  """
    특정 조건에 맞는 기업의 재무제표 데이터를 필터링합니다.
    """
  try:
    service = FinancialDataService()
    results = await service.filter_financial_data(industry=request.industry,
                                                  min_revenue=request.min_revenue,
                                                  max_debt_ratio=request.max_debt_ratio,
                                                  top_k=request.top_k)
    return results
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"재무제표 데이터 필터링 중 오류 발생: {str(e)}")
