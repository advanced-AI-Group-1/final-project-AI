from typing import Dict, Any, Optional
from app.infrastructure.llm.runpod_manager import RunPodLLMManager
from app.infrastructure.llm.prompt_templates import format_financial_data_for_credit_rating


class CreditRatingService:
  """
    신용등급 평가 서비스
    """

  def __init__(self):
    self.llm_manager = RunPodLLMManager()

  def _format_financial_data_for_credit_rating(self, financial_data: Dict[str, Any]) -> str:
    """
        신용등급 평가를 위한 재무 데이터 포맷팅
        
        Args:
            financial_data (Dict[str, Any]): 재무 데이터
            
        Returns:
            str: 포맷팅된 재무 데이터 텍스트
        """
    return format_financial_data_for_credit_rating(financial_data)

  async def evaluate_credit_rating(self,
                                   company_name: str,
                                   financial_data: Dict[str, Any],
                                   additional_context: Optional[str] = None) -> Dict[str, Any]:
    """
        재무제표 데이터를 기반으로 LLM을 사용하여 신용평가 등급을 산출합니다.
        
        Args:
            company_name (str): 회사명
            financial_data (Dict[str, Any]): 재무 데이터
            additional_context (Optional[str], optional): 추가 컨텍스트. 기본값은 None.
            
        Returns:
            Dict[str, Any]: 신용등급 평가 결과
        """
    # 프롬프트 생성
    instruction = "다음 재무 정보를 바탕으로 기업의 신용등급을 평가해주세요."
    input_text = self._format_financial_data_for_credit_rating(financial_data)
    if additional_context:
      input_text += f"\n\n추가 정보: {additional_context}"

    # LLM 응답 생성
    response = await self.llm_manager.generate_response(instruction, input_text)

    # 응답 파싱 (예시)
    # 실제로는 응답 텍스트를 파싱하여 신용등급 정보를 추출해야 함
    credit_rating_result = {
        "company_name": company_name,
        "credit_rating": "A",  # 실제로는 응답에서 파싱
        "rating_details": {
            "financial_strength": "Strong",
            "business_risk": "Moderate",
            "industry_outlook": "Stable"
        },
        "confidence_score": 0.85
    }

    return credit_rating_result

  async def submit_credit_rating_request(self,
                                         company_name: str,
                                         financial_data: Dict[str, Any],
                                         additional_context: Optional[str] = None) -> str:
    """
        신용등급 평가 요청을 제출하고 요청 ID를 반환합니다.
        
        Args:
            company_name (str): 회사명
            financial_data (Dict[str, Any]): 재무 데이터
            additional_context (Optional[str], optional): 추가 컨텍스트. 기본값은 None.
            
        Returns:
            str: 요청 ID
        """
    # 프롬프트 생성
    instruction = "다음 재무 정보를 바탕으로 기업의 신용등급을 평가해주세요."
    input_text = self._format_financial_data_for_credit_rating(financial_data)
    if additional_context:
      input_text += f"\n\n추가 정보: {additional_context}"

    # 비동기 요청 제출
    request_id = await self.llm_manager.submit_request(instruction, input_text)
    return request_id
