from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

from app.domain.credit_rating.service import CreditRatingService
from app.infrastructure.llm.runpod_manager import RunPodLLMManager

router = APIRouter()


class FinancialData(BaseModel):
  """재무제표 데이터 모델 - 영어 컬럼명 사용"""
  corp_code: str = Field(..., description="기업 코드")
  corp_name: str = Field(..., description="기업명")
  market_type: str = Field(..., description="시장 구분")
  industry_name: str = Field(..., description="산업 분류")
  revenue: float = Field(..., description="매출액")
  operating_profit: float = Field(..., description="영업이익")
  net_income: float = Field(..., description="당기순이익")
  total_assets: float = Field(..., description="총자산")
  total_liabilities: float = Field(..., description="총부채")
  total_equity: float = Field(..., description="자본총계")
  capital: Optional[float] = Field(None, description="자본금")
  operating_cash_flow: Optional[float] = Field(None, description="영업활동현금흐름")
  interest_bearing_debt: Optional[float] = Field(None, description="이자발생부채")
  debt_ratio: Optional[float] = Field(None, description="부채비율")
  ROA: Optional[float] = Field(None, description="ROA")
  ROE: Optional[float] = Field(None, description="ROE")
  asset_turnover_ratio: Optional[float] = Field(None, description="매출총자산회전율")
  interest_to_assets_ratio: Optional[float] = Field(None, description="이자총자산비율")
  interest_to_revenue_ratio: Optional[float] = Field(None, description="이자매출비율")
  cash_flow_to_interest: Optional[float] = Field(None, description="현금흐름대비이자")
  interest_to_cash_flow: Optional[float] = Field(None, description="이자대비현금흐름")
  log_total_assets: Optional[float] = Field(None, description="로그총자산")
  log_total_liabilities: Optional[float] = Field(None, description="로그총부채")
  is_consolidated: Optional[str] = Field(None, description="연결재무제표 여부")


class CreditRatingRequest(BaseModel):
  company_name: str
  financial_data: FinancialData
  additional_context: Optional[str] = None


class CreditRatingResponse(BaseModel):
  company_name: str
  credit_rating: str
  rating_details: Dict[str, Any]
  confidence_score: float


class CreditRatingRequestSubmitResponse(BaseModel):
  request_id: str
  status: str
  message: str


class CreditRatingStatusResponse(BaseModel):
  request_id: str
  status: str
  message: Optional[str] = None
  result: Optional[CreditRatingResponse] = None
  timestamp: Optional[str] = None


@router.post("/evaluate", response_model=CreditRatingResponse)
async def evaluate_credit_rating(request: CreditRatingRequest):
  """
    재무제표 데이터를 기반으로 LLM을 사용하여 신용평가 등급을 산출합니다.
    
    요청이 완료될 때까지 응답을 기다립니다. 처리 시간이 길 수 있으므로, 
    비동기 처리가 필요한 경우 /evaluate-async 엔드포인트를 사용하세요.
    """
  try:
    service = CreditRatingService()
    result = await service.evaluate_credit_rating(request.company_name, request.financial_data.dict(),
                                                  request.additional_context)
    return result
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"신용평가 등급 산출 중 오류 발생: {str(e)}")


@router.post("/evaluate-async", response_model=CreditRatingRequestSubmitResponse)
async def evaluate_credit_rating_async(request: CreditRatingRequest, background_tasks: BackgroundTasks):
  """
    재무제표 데이터를 기반으로 LLM을 사용하여 비동기적으로 신용평가 등급을 산출합니다.
    
    요청 예시:
    ```json
    {
      "company_name": "테스트기업",
      "financial_data": {
        "corp_code": "123456",
        "corp_name": "테스트기업",
        "market_type": "코스닥시장상장법인",
        "industry_name": "소프트웨어 개발 및 공급업",
        "revenue": 1000000000,
        "operating_profit": 150000000,
        "net_income": 100000000,
        "total_assets": 2000000000,
        "total_liabilities": 1000000000,
        "total_equity": 1000000000,
        "debt_ratio": 50.0,
        "ROA": 5.0,
        "ROE": 10.0,
        "asset_turnover_ratio": 0.5,
        "interest_to_assets_ratio": 0.02,
        "interest_to_revenue_ratio": 0.04,
        "cash_flow_to_interest": 5.0,
        "interest_to_cash_flow": 0.2,
        "operating_cash_flow": 120000000,
        "interest_bearing_debt": 800000000
      }
    }
    ```
    
    응답으로 요청 ID가 반환되며, 이 ID를 사용하여 /status/{request_id} 엔드포인트에서 결과를 조회할 수 있습니다.
    """
  try:
    # 신용등급 평가 서비스 초기화
    service = CreditRatingService()

    # 프롬프트 생성
    instruction = "다음 재무 정보를 바탕으로 기업의 신용등급을 평가해주세요."
    input_text = service._format_financial_data_for_credit_rating(request.financial_data.dict())
    if request.additional_context:
      input_text += f"\n\n추가 정보: {request.additional_context}"

    # RunPod LLM 매니저 초기화
    llm_manager = RunPodLLMManager()

    # 비동기 요청 제출
    request_id = await llm_manager.submit_request(instruction, input_text)

    # 백그라운드 작업으로 결과 처리
    background_tasks.add_task(llm_manager.process_request_background, request_id, request.company_name,
                              request.financial_data.dict())

    return {
        "request_id": request_id,
        "status": "PENDING",
        "message": "신용등급 평가 요청이 성공적으로 제출되었습니다. 결과를 조회하려면 /status/{request_id} 엔드포인트를 사용하세요."
    }
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"신용평가 등급 요청 제출 중 오류 발생: {str(e)}")


@router.get("/status/{request_id}", response_model=CreditRatingStatusResponse)
async def get_credit_rating_status(request_id: str):
  """
    신용등급 평가 요청의 상태를 조회합니다.
    
    Args:
        request_id: 이전에 /evaluate-async 엔드포인트에서 반환된 요청 ID
        
    Returns:
        요청 상태 및 결과 (완료된 경우)
    """
  try:
    llm_manager = RunPodLLMManager()
    result = llm_manager.get_request_status(request_id)

    response = {
        "request_id": request_id,
        "status": result.get("status", "UNKNOWN"),
        "message": result.get("message"),
        "timestamp": result.get("timestamp")
    }

    # 결과가 완료된 경우 결과 포함
    if result.get("status") == "COMPLETED" and "result" in result:
      response["result"] = result["result"]

    return response
  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"신용등급 평가 상태 조회 중 오류 발생: {str(e)}")
