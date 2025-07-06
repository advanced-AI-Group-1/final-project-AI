from fastapi import APIRouter, HTTPException, Request, Depends
from sse_starlette.sse import EventSourceResponse

from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json

from app.domain.report_generation.service import ReportGenerationService
from app.domain.credit_rating.service import CreditRatingService
from app.domain.credit_rating.sse_service import SSECreditRatingService
from app.domain.report_generation.sse_service import SSEReportGenerationService
from app.domain.sse.service import SSEService

router = APIRouter()


class CreditRatingResult(BaseModel):
  credit_rating: str
  rating_details: Optional[Dict[str, str]] = None
  confidence_score: Optional[float] = None
  
  def to_dict(self) -> Dict[str, Any]:
    """Pydantic 모델을 딕셔너리로 변환합니다."""
    return {
        "credit_rating": self.credit_rating,
        "rating_details": self.rating_details,
        "confidence_score": self.confidence_score
    }


class ReportGenerationRequest(BaseModel):
  company_name: str
  credit_rating_result: CreditRatingResult
  financial_data: Dict[str, Any]
  report_type: str = "agent_based"  # standard, detailed, executive_summary, agent_based 등


class ReportData(BaseModel):
  company_name: str
  subtitle: str
  summary_content: str
  detailed_content: str
  generation_date: str
  industry_name: str
  market_type: str


class ReportSection(BaseModel):
  title: str
  description: str
  content: str


class ReportResponse(BaseModel):
  company_name: str
  report_data: ReportData
  sections: List[ReportSection]
  credit_rating: CreditRatingResult
  generated_at: str
  report_type: str
  summary_card_structured: Optional[Dict[str, Any]] = None
  news_data: Optional[List[Dict[str, Any]]] = None


class FinancialDataOnlyRequest(BaseModel):
  company_name: str
  financial_data: Dict[str, Any]
  unit: Optional[str] = "원"  # 기본값은 "원"
  positive_factors: Optional[List[str]] = None
  negative_factors: Optional[List[str]] = None
  report_type: str = "agent_based"


@router.post("/generate", response_model=ReportResponse)
async def generate_report(request: ReportGenerationRequest):
  """
  신용평가 결과와 재무제표 데이터를 기반으로 AI 에이전트를 통해 보고서를 생성합니다.
  """
  try:
    service = ReportGenerationService()
    
    # CreditRatingResult 객체를 딕셔너리로 변환
    credit_rating_dict = request.credit_rating_result.to_dict()
    
    result = await service.generate_report(request.company_name, credit_rating_dict, request.financial_data,
                                           request.report_type)
    return result
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"보고서 생성 중 오류 발생: {str(e)}")


@router.post("/generate-from-financial-data", response_model=ReportResponse)
async def generate_report_from_financial_data(request: FinancialDataOnlyRequest):
  """
  재무제표 데이터만 받아서 신용등급 평가부터 보고서 생성까지 한번에 처리합니다.
  
  1. 재무제표 데이터를 바탕으로 신용등급을 평가합니다.
  2. 평가된 신용등급과 재무제표 데이터를 바탕으로 보고서를 생성합니다.
  """
  try:
    # 1. 신용등급 평가
    credit_rating_service = CreditRatingService()
    
    # 재무 데이터에 회사명 추가
    financial_data = request.financial_data.copy()
    financial_data['company_name'] = request.company_name
    
    # positive_factors와 negative_factors가 있으면 추가
    if request.positive_factors:
      financial_data['positive_factors'] = request.positive_factors
    if request.negative_factors:
      financial_data['negative_factors'] = request.negative_factors
    
    # 단위 정보 추가
    financial_data['unit'] = request.unit
    
    # 신용등급 평가
    credit_rating_result = await credit_rating_service.evaluate_credit_rating(financial_data)

    # 2. 신용등급 결과를 CreditRatingResult 모델로 변환
    credit_rating_model = CreditRatingResult(credit_rating=credit_rating_result.get("credit_rating", "N/A"),
                                           rating_details=credit_rating_result.get("rating_details"),
                                           confidence_score=credit_rating_result.get("confidence_score"))

    # 3. CreditRatingResult 객체를 딕셔너리로 변환 (ReportState 모델과의 호환성을 위해)
    credit_rating_dict = credit_rating_model.to_dict()
    
    # 4. 보고서 생성
    report_service = ReportGenerationService()
    result = await report_service.generate_report(request.company_name, credit_rating_dict, financial_data, request.report_type)
    
    return result
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"보고서 생성 중 오류 발생: {str(e)}")


@router.post("/generate-from-financial-data/sse")
async def generate_report_from_financial_data_sse(request: FinancialDataOnlyRequest):
  """
  재무제표 데이터만 받아서 신용등급 평가부터 보고서 생성까지 한번에 처리하고 SSE로 진행 상황을 전송합니다.
  
  1. 재무제표 데이터를 바탕으로 신용등급을 평가하고 진행 상황을 SSE로 전송합니다.
  2. 평가된 신용등급과 재무제표 데이터를 바탕으로 보고서를 생성하고 진행 상황을 SSE로 전송합니다.
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
    
    # 단위 정보 추가
    financial_data['unit'] = request.unit
    
    async def event_generator():
      try:
        # 1. 신용등급 평가 (SSE 지원)
        credit_rating_service = SSECreditRatingService()
        credit_rating_result = None
        
        async for event in credit_rating_service.evaluate_credit_rating_with_sse(financial_data):
          # 신용등급 평가 결과 저장
          if event["data"]:
            data = json.loads(event["data"])  # JSON 문자열을 파이썬 객체로 변환
            if "result" in data:
              credit_rating_result = data["result"]
          
          # 이벤트 전달
          yield event
        
        # 신용등급 평가 결과가 없으면 오류
        if not credit_rating_result:
          raise ValueError("신용등급 평가 결과를 받지 못했습니다.")
        
        # 2. 신용등급 결과를 CreditRatingResult 모델로 변환
        credit_rating_model = CreditRatingResult(
          credit_rating=credit_rating_result.get("credit_rating", "N/A"),
          rating_details=credit_rating_result.get("rating_details"),
          confidence_score=credit_rating_result.get("confidence_score")
        )
        
        # 3. CreditRatingResult 객체를 딕셔너리로 변환
        credit_rating_dict = credit_rating_model.to_dict()
        
        # 4. 보고서 생성 (SSE 지원)
        report_service = SSEReportGenerationService()
        
        async for event in report_service.generate_report_with_sse(
          request.company_name, credit_rating_dict, financial_data, request.report_type
        ):
          yield event
      
      except Exception as e:
        # 오류 발생 시 오류 이벤트 전송
        sse_service = SSEService()
        yield sse_service._format_event(
          event="error",
          data={
            "step": "error",
            "message": f"처리 중 오류가 발생했습니다: {str(e)}",
            "error": str(e)
          }
        )
    
    return EventSourceResponse(event_generator())
  
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"SSE 스트림 설정 중 오류 발생: {str(e)}")
