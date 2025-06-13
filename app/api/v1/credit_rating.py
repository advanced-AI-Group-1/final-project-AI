from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from app.domain.credit_rating.service import CreditRatingService

router = APIRouter()

class CreditRatingRequest(BaseModel):
    company_name: str
    financial_data: Dict[str, Any]
    additional_context: Optional[str] = None

class CreditRatingResponse(BaseModel):
    company_name: str
    credit_rating: str
    rating_details: Dict[str, Any]
    confidence_score: float

@router.post("/evaluate", response_model=CreditRatingResponse)
async def evaluate_credit_rating(request: CreditRatingRequest):
    """
    재무제표 데이터를 기반으로 LLM을 사용하여 신용평가 등급을 산출합니다.
    """
    try:
        service = CreditRatingService()
        result = await service.evaluate_credit_rating(
            request.company_name,
            request.financial_data,
            request.additional_context
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"신용평가 등급 산출 중 오류 발생: {str(e)}")
