from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from app.domain.report_generation.service import ReportGenerationService

router = APIRouter()

class ReportGenerationRequest(BaseModel):
    company_name: str
    credit_rating_result: Dict[str, Any]
    financial_data: Dict[str, Any]
    report_type: str = "standard"  # standard, detailed, executive_summary 등
    additional_context: Optional[str] = None

class ReportResponse(BaseModel):
    company_name: str
    report_content: str
    report_sections: List[Dict[str, Any]]
    generated_at: str
    report_type: str

@router.post("/generate", response_model=ReportResponse)
async def generate_report(request: ReportGenerationRequest):
    """
    신용평가 결과와 재무제표 데이터를 기반으로 AI 에이전트를 통해 보고서를 생성합니다.
    """
    try:
        service = ReportGenerationService()
        result = await service.generate_report(
            request.company_name,
            request.credit_rating_result,
            request.financial_data,
            request.report_type,
            request.additional_context
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"보고서 생성 중 오류 발생: {str(e)}")
