from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging

from app.domain.credit_rating.service import CreditRatingService
from app.infrastructure.llm.runpod_manager import RunPodLLMManager

# 로깅 설정
logger = logging.getLogger(__name__)

router = APIRouter()

# 신용등급 평가 응답 모델
class CreditRatingResponse(BaseModel):
  """
    신용등급 평가 응답 모델
    """
  company_name: str
  credit_rating: str
  confidence_score: float
  raw_response: str
  positive_factors: List[str] = []
  negative_factors: List[str] = []


# 신용등급 평가 요청 상태 응답 모델
class CreditRatingStatusResponse(BaseModel):
  """
    신용등급 평가 요청 상태 응답 모델
    """
  status: str
  message: str
  result: Optional[Dict[str, Any]] = None


# 신용등급 평가 요청 제출 응답 모델
class CreditRatingRequestSubmitResponse(BaseModel):
  """
    신용등급 평가 요청 제출 응답 모델
    """
  request_id: str
  status: str
  message: str


class CreditRatingRequest(BaseModel):
  """
  신용등급 평가 요청 모델
  """
  company_name: str
  financial_data: Dict[str, Any]
  unit: Optional[str] = "억원"  # "억원" 또는 "원", 기본값은 "억원"
  positive_factors: Optional[List[str]] = None
  negative_factors: Optional[List[str]] = None
  additional_context: Optional[str] = None


@router.post("/evaluate", response_model=CreditRatingResponse)
async def evaluate_credit_rating(
    request: CreditRatingRequest,
    credit_rating_service: CreditRatingService = Depends()
):
  """
  신용등급 평가 API
  
  Args:
      request (CreditRatingRequest): 신용등급 평가 요청 모델
      credit_rating_service (CreditRatingService): 신용등급 평가 서비스
      
  Returns:
      CreditRatingResponse: 신용등급 평가 결과
  """
  try:
    # 재무 데이터에 회사명 추가
    financial_data = request.financial_data.copy()
    financial_data['company_name'] = request.company_name
    
    # positive_factors와 negative_factors가 있으면 추가
    if request.positive_factors:
      financial_data['positive_factors'] = request.positive_factors
    if request.negative_factors:
      financial_data['negative_factors'] = request.negative_factors
    
    # 추가 컨텍스트가 있으면 추가
    if request.additional_context:
      financial_data['additional_context'] = request.additional_context
    
    # 단위 정보 추가
    financial_data['unit'] = request.unit
    
    # 신용등급 평가 - await 키워드 추가
    result = await credit_rating_service.evaluate_credit_rating(financial_data)
    return result
  except Exception as e:
    logger.error(f"신용등급 평가 중 오류 발생: {str(e)}")
    raise HTTPException(status_code=500, detail=f"신용등급 평가 중 오류 발생: {str(e)}")


@router.post("/evaluate-async", response_model=CreditRatingRequestSubmitResponse)
async def evaluate_credit_rating_async(
    request: CreditRatingRequest,
    background_tasks: BackgroundTasks,
    llm_manager: RunPodLLMManager = Depends()
):
  """
  비동기 신용등급 평가 API
  
  Args:
      request (CreditRatingRequest): 신용등급 평가 요청 모델
      background_tasks (BackgroundTasks): 백그라운드 작업
      llm_manager (RunPodLLMManager): RunPod LLM 매니저
      
  Returns:
      CreditRatingRequestSubmitResponse: 신용등급 평가 요청 제출 결과
  """
  try:
    # 재무 데이터에 회사명 추가
    financial_data = request.financial_data.copy()
    financial_data['company_name'] = request.company_name
    
    # positive_factors와 negative_factors가 있으면 추가
    if request.positive_factors:
      financial_data['positive_factors'] = request.positive_factors
    if request.negative_factors:
      financial_data['negative_factors'] = request.negative_factors
    
    # 추가 컨텍스트가 있으면 추가
    if request.additional_context:
      financial_data['additional_context'] = request.additional_context
    
    # 단위 정보 추가
    financial_data['unit'] = request.unit
    
    # 신용등급 평가 요청 제출
    credit_rating_service = CreditRatingService()
    prompt = credit_rating_service._format_financial_data_for_credit_rating(financial_data)
    
    # RunPod API 요청 제출
    request_id = await llm_manager.submit_request(prompt)
    
    # 백그라운드 작업 등록
    background_tasks.add_task(
        llm_manager.process_request_background,
        request_id,
        request.company_name,
        financial_data
    )
    
    return {
        "request_id": request_id,
        "status": "SUBMITTED",
        "message": "신용등급 평가 요청이 제출되었습니다."
    }
  except Exception as e:
    logger.error(f"비동기 신용등급 평가 요청 제출 중 오류 발생: {str(e)}")
    raise HTTPException(status_code=500, detail=f"비동기 신용등급 평가 요청 제출 중 오류 발생: {str(e)}")


@router.get("/status/{request_id}", response_model=CreditRatingStatusResponse)
async def get_credit_rating_status(request_id: str):
  """
    신용등급 평가 요청 상태를 조회합니다.
    """
  try:
    llm_manager = RunPodLLMManager()
    result = llm_manager.get_request_status(request_id)
    
    # 응답 구조 변환
    response = {
        "status": result.get("status", "UNKNOWN"),
        "message": result.get("message", ""),
        "result": result.get("result")
    }
    
    return response
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"신용평가 등급 상태 조회 중 오류 발생: {str(e)}")
