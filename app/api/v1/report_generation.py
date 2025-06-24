from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from app.domain.report_generation.service import ReportGenerationService
from app.domain.credit_rating.service import CreditRatingService

router = APIRouter()


class CreditRatingResult(BaseModel):
  credit_rating: str
  rating_details: Optional[Dict[str, str]] = None
  confidence_score: Optional[float] = None


class ReportGenerationRequest(BaseModel):
  company_name: str
  credit_rating_result: CreditRatingResult
  financial_data: Dict[str, Any]
  report_type: str = "standard"  # standard, detailed, executive_summary, agent_based 등
  additional_context: Optional[str] = None


class ReportResponse(BaseModel):
  company_name: str
  report_content: str
  report_sections: List[Dict[str, Any]]
  generated_at: str
  report_type: str


class AgentBasedReportResponse(BaseModel):
  company_name: str
  summary_card: str
  detailed_report: str
  html_report: str
  sections: List[Dict[str, Any]]
  generated_at: str
  report_type: str


class HtmlConversionRequest(BaseModel):
  company_name: str
  report_content: str


class HtmlConversionResponse(BaseModel):
  html_report: str


class FinancialDataOnlyRequest(BaseModel):
  company_name: str
  financial_data: Dict[str, Any]
  report_type: str = "agent_based"
  additional_context: Optional[str] = None


@router.post("/generate", response_model=ReportResponse)
async def generate_report(request: ReportGenerationRequest):
  """
    신용평가 결과와 재무제표 데이터를 기반으로 AI 에이전트를 통해 보고서를 생성합니다.
    """
  try:
    service = ReportGenerationService()
    result = await service.generate_report(request.company_name, request.credit_rating_result, request.financial_data,
                                           request.report_type, request.additional_context)
    return result
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"보고서 생성 중 오류 발생: {str(e)}")


@router.post("/generate-agent-based", response_model=AgentBasedReportResponse)
async def generate_agent_based_report(request: ReportGenerationRequest):
  """
    LangGraph 기반 에이전트를 사용하여 신용평가 보고서를 생성합니다.
    이 엔드포인트는 요약 카드, 상세 보고서, HTML 보고서를 포함한 결과를 반환합니다.
    """
  try:
    service = ReportGenerationService()
    # report_type을 agent_based로 강제 설정
    request.report_type = "agent_based"
    result = await service.generate_report(request.company_name, request.credit_rating_result, request.financial_data,
                                           request.report_type, request.additional_context)
    return result
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"에이전트 기반 보고서 생성 중 오류 발생: {str(e)}")


@router.post("/convert-to-html", response_model=HtmlConversionResponse)
async def convert_report_to_html(request: HtmlConversionRequest):
  """
    마크다운 형식의 보고서를 HTML로 변환합니다.
    """
  try:
    service = ReportGenerationService()
    html_report = await service.generate_html_report(request.company_name, request.report_content)
    return {"html_report": html_report}
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"HTML 변환 중 오류 발생: {str(e)}")


@router.post("/generate-from-financial-data", response_model=AgentBasedReportResponse)
async def generate_report_from_financial_data(request: FinancialDataOnlyRequest):
  """
    재무제표 데이터만 받아서 신용등급 평가부터 보고서 생성까지 한번에 처리합니다.
    
    1. 재무제표 데이터를 바탕으로 신용등급을 평가합니다.
    2. 평가된 신용등급과 재무제표 데이터를 바탕으로 보고서를 생성합니다.
    """
  try:
    # 1. 신용등급 평가
    credit_rating_service = CreditRatingService()
    credit_rating_result = await credit_rating_service.evaluate_credit_rating(request.company_name,
                                                                              request.financial_data,
                                                                              request.additional_context)

    # 2. 신용등급 결과를 CreditRatingResult 모델로 변환
    credit_rating_model = CreditRatingResult(credit_rating=credit_rating_result.get("credit_rating", "N/A"),
                                             rating_details=credit_rating_result.get("rating_details"),
                                             confidence_score=credit_rating_result.get("confidence_score"))

    # 3. CreditRatingResult 객체를 딕셔너리로 변환 (ReportState 모델과의 호환성을 위해)
    credit_rating_dict = {
        "credit_rating": credit_rating_model.credit_rating,
        "rating_details": credit_rating_model.rating_details,
        "confidence_score": credit_rating_model.confidence_score
    }

    # 4. 보고서 생성 (딕셔너리로 변환된 credit_rating 전달)
    report_service = ReportGenerationService()
    result = await report_service.generate_report(request.company_name, credit_rating_dict, request.financial_data,
                                                  request.report_type, request.additional_context)

    return result
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"보고서 생성 중 오류 발생: {str(e)}")
