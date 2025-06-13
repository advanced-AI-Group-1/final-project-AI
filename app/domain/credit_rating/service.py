from typing import Dict, Any, Optional
from app.infrastructure.llm.manager import LLMManager
from datetime import datetime

class CreditRatingService:
    """
    재무제표 데이터를 기반으로 신용평가 등급을 산출하는 서비스 클래스
    """
    def __init__(self):
        self.llm_manager = LLMManager()
        
    async def evaluate_credit_rating(
        self, 
        company_name: str, 
        financial_data: Dict[str, Any],
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        LLM을 사용하여 재무제표 데이터를 기반으로 신용평가 등급을 산출합니다.
        
        Args:
            company_name (str): 기업명
            financial_data (Dict[str, Any]): 재무제표 데이터
            additional_context (Optional[str]): 추가 컨텍스트 정보
            
        Returns:
            Dict[str, Any]: 신용평가 결과
        """
        # LLM에 전달할 프롬프트 구성
        prompt = self._construct_credit_rating_prompt(company_name, financial_data, additional_context)
        
        # LLM을 통한 신용평가 수행
        llm_response = await self.llm_manager.generate_response(prompt)
        
        # LLM 응답 파싱 및 결과 구조화
        rating_result = self._parse_llm_response(llm_response)
        
        # 결과에 기업명과 평가 시간 추가
        rating_result["company_name"] = company_name
        rating_result["evaluation_timestamp"] = datetime.now().isoformat()
        
        return {
            "company_name": company_name,
            "credit_rating": rating_result.get("credit_rating", "N/A"),
            "rating_details": rating_result.get("rating_details", {}),
            "confidence_score": rating_result.get("confidence_score", 0.0)
        }
        
    def _construct_credit_rating_prompt(
        self, 
        company_name: str, 
        financial_data: Dict[str, Any],
        additional_context: Optional[str]
    ) -> str:
        """
        신용평가를 위한 LLM 프롬프트를 구성합니다.
        """
        prompt = f"""
        당신은 금융 전문가로서 기업의 재무제표를 분석하여 신용평가 등급을 산출하는 역할을 합니다.
        
        다음은 {company_name} 기업의 재무제표 데이터입니다:
        
        {financial_data}
        
        위 재무제표를 분석하여 다음 정보를 포함한 신용평가 결과를 JSON 형식으로 제공해주세요:
        
        1. credit_rating: 신용등급 (AAA, AA, A, BBB, BB, B, CCC, CC, C, D 중 하나)
        2. rating_details: 신용등급 산출 근거 및 세부 분석 (수익성, 안정성, 성장성, 현금흐름 등)
        3. confidence_score: 신용등급 평가의 신뢰도 점수 (0.0 ~ 1.0)
        
        """
        
        if additional_context:
            prompt += f"\n추가 컨텍스트 정보:\n{additional_context}\n"
            
        return prompt
        
    def _parse_llm_response(self, llm_response: str) -> Dict[str, Any]:
        """
        LLM 응답을 파싱하여 구조화된 결과로 변환합니다.
        실제 구현에서는 JSON 파싱 등의 로직이 필요합니다.
        """
        # 실제 구현에서는 LLM 응답을 파싱하는 로직 필요
        # 여기서는 간단한 예시만 제공
        import json
        try:
            return json.loads(llm_response)
        except:
            # 파싱 실패 시 기본값 반환
            return {
                "credit_rating": "N/A",
                "rating_details": {
                    "error": "LLM 응답 파싱 실패"
                },
                "confidence_score": 0.0
            }
