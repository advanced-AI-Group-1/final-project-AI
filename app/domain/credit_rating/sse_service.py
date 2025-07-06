"""
SSE를 지원하는 신용등급 평가 서비스
"""
import asyncio
import logging
from typing import Dict, Any, AsyncGenerator, Optional, List, Callable

from app.domain.credit_rating.service import CreditRatingService
from app.domain.sse.service import SSEService, ProcessStep

logger = logging.getLogger(__name__)

class SSECreditRatingService(CreditRatingService):
    """SSE를 지원하는 신용등급 평가 서비스"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        super().__init__(openai_api_key)
        self.sse_service = SSEService()
    
    async def evaluate_credit_rating_with_sse(self, financial_data: Dict[str, Any]) -> AsyncGenerator:
        """
        재무 데이터를 기반으로 신용등급을 평가하고 진행 상황을 SSE로 전송합니다.
        
        Args:
            financial_data: 재무 데이터
            
        Returns:
            AsyncGenerator: SSE 이벤트 생성기
        """
        company_name = financial_data.get('company_name', '알_수_없음')
        
        try:
            # 신용등급 평가 시작 이벤트
            yield self.sse_service._format_event(
                event="message",
                data={
                    "step": ProcessStep.CREDIT_RATING_STARTED,
                    "message": f"{company_name} 기업의 신용등급 평가를 시작합니다.",
                    "progress": 10
                }
            )
            await asyncio.sleep(0.1)
            
            # 파생 지표 계산 및 데이터 전처리
            financial_data = self._calculate_derived_metrics(financial_data)
            
            # 데이터 전처리 완료 이벤트
            yield self.sse_service._format_event(
                event="message",
                data={
                    "step": ProcessStep.CREDIT_RATING_PROCESSING,
                    "message": "재무 데이터 전처리 완료, 신용등급 평가 중...",
                    "progress": 30
                }
            )
            await asyncio.sleep(0.1)
            
            # Tavily 검색 및 LLM 요청 준비
            has_positive_factors = ('positive_factors' in financial_data and
                                  financial_data['positive_factors'] is not None and
                                  financial_data['positive_factors'])
            has_negative_factors = ('negative_factors' in financial_data and
                                  financial_data['negative_factors'] is not None and
                                  financial_data['negative_factors'])
            
            # 둘 다 null인 경우에만 Tavily 검색 수행
            if not has_positive_factors and not has_negative_factors:
                yield self.sse_service._format_event(
                    event="message",
                    data={
                        "step": ProcessStep.CREDIT_RATING_PROCESSING,
                        "message": f"{company_name} 기업의 추가 정보를 검색 중...",
                        "progress": 40
                    }
                )
                await asyncio.sleep(0.1)
                
                search_results = await self.tavily_search_service.search_company_factors(
                    company_name, financial_data.get('industry_name')
                )
                
                # 검색 결과가 있으면 financial_data에 추가
                if search_results["positive_factors"]:
                    financial_data["positive_factors"] = search_results["positive_factors"]
                
                if search_results["negative_factors"]:
                    financial_data["negative_factors"] = search_results["negative_factors"]
            
            # LLM 요청 이벤트
            yield self.sse_service._format_event(
                event="message",
                data={
                    "step": ProcessStep.CREDIT_RATING_PROCESSING,
                    "message": "AI 모델을 통한 신용등급 평가 중...",
                    "progress": 50
                }
            )
            await asyncio.sleep(0.1)
            
            # 프롬프트 생성
            prompt = self._format_financial_data_for_credit_rating(financial_data)
            
            # LLM 요청
            response = await self.llm_manager.request(prompt)
            
            # 응답 파싱 이벤트
            yield self.sse_service._format_event(
                event="message",
                data={
                    "step": ProcessStep.CREDIT_RATING_PROCESSING,
                    "message": "AI 응답 분석 및 신용등급 확정 중...",
                    "progress": 70
                }
            )
            await asyncio.sleep(0.1)
            
            # 응답 파싱
            result = self._parse_credit_rating_response(response, company_name)
            
            # 파싱된 결과에 긍정적/부정적 요소가 없으면 검색 결과 사용
            if not result["positive_factors"] and "positive_factors" in financial_data and financial_data["positive_factors"]:
                result["positive_factors"] = financial_data["positive_factors"]
            
            if not result["negative_factors"] and "negative_factors" in financial_data and financial_data["negative_factors"]:
                result["negative_factors"] = financial_data["negative_factors"]
            
            # 원본 ML 예측 결과 저장
            result["ml_predicted_rating"] = result["credit_rating"]
            
            # 룰 기반 검증 및 조정
            yield self.sse_service._format_event(
                event="message",
                data={
                    "step": ProcessStep.CREDIT_RATING_PROCESSING,
                    "message": "신용등급 검증 및 조정 중...",
                    "progress": 80
                }
            )
            await asyncio.sleep(0.1)
            
            # 룰 기반 검증 및 조정 로직 실행
            adjusted_rating, adjustment_reason = comprehensive_credit_validation(
                financial_data, result["credit_rating"]
            )
            
            # 에이전트 검증이 필요한지 확인
            needs_agent_validation = True
            
            # 명확한 케이스 확인 (에이전트 검증 생략)
            if adjusted_rating in ['D']:
                needs_agent_validation = False
            elif financial_data.get('total_equity', 1) <= 0:
                needs_agent_validation = False
            elif financial_data.get('total_liabilities', 0) > financial_data.get('total_assets', 0):
                needs_agent_validation = False
            elif (financial_data.get('operating_cash_flow', 0) < 0 and
                  financial_data.get('interest_expense', 0) > 0 and
                  abs(financial_data['operating_cash_flow']) > financial_data['interest_expense']):
                needs_agent_validation = False
            elif adjusted_rating == 'AAA' and \
                financial_data.get('debt_ratio', 0) < 0.5 and \
                financial_data.get('current_ratio', 0) > 1.2 and \
                financial_data.get('operating_profit_margin', 0) > 0.08:
                needs_agent_validation = False
            
            # 에이전트 검증 실행
            if needs_agent_validation:
                yield self.sse_service._format_event(
                    event="message",
                    data={
                        "step": ProcessStep.CREDIT_RATING_PROCESSING,
                        "message": "AI 에이전트를 통한 신용등급 최종 검증 중...",
                        "progress": 90
                    }
                )
                await asyncio.sleep(0.1)
                
                agent_result = await self.credit_rating_agent.validate_rating(
                    financial_data=financial_data,
                    initial_rating=adjusted_rating,
                    validation_issues=[adjustment_reason] if adjustment_reason else []
                )
                
                final_rating = agent_result.get("final_rating", adjusted_rating)
                final_reason = agent_result.get("final_reason", "")
                is_adjusted = agent_result.get("is_adjusted", False)
                
                # 에이전트가 등급을 조정한 경우
                if is_adjusted and final_rating != adjusted_rating:
                    adjusted_rating = final_rating
                    adjustment_reason = f"{adjustment_reason}\n에이전트 조정: {final_reason}"
            
            # 최종 결과 반영
            result["credit_rating"] = adjusted_rating
            result["adjustment_reason"] = adjustment_reason
            result["agent_validation_skipped"] = not needs_agent_validation
            
            # 신용등급 평가 완료 이벤트
            yield self.sse_service._format_event(
                event="message",
                data={
                    "step": ProcessStep.CREDIT_RATING_COMPLETED,
                    "message": f"{company_name} 기업의 신용등급 평가가 완료되었습니다: {result['credit_rating']}",
                    "progress": 100,
                    "result": result
                }
            )
            
        except Exception as e:
            logger.error(f"신용등급 평가 중 오류 발생: {str(e)}")
            # 오류 이벤트 전송
            yield self.sse_service._format_event(
                event="error",
                data={
                    "step": ProcessStep.ERROR,
                    "message": f"신용등급 평가 중 오류가 발생했습니다: {str(e)}",
                    "error": str(e)
                }
            )
            raise ValueError(f"신용등급 평가 중 오류 발생: {str(e)}")

# 필요한 함수 임포트
from app.domain.credit_rating.validation import comprehensive_credit_validation
