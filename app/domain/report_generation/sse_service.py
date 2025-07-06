"""
SSE를 지원하는 보고서 생성 서비스
"""
import asyncio
import logging
from typing import Dict, Any, AsyncGenerator, Optional, Callable

from app.domain.report_generation.service import ReportGenerationService
from app.domain.sse.service import SSEService, ProcessStep

logger = logging.getLogger(__name__)


class SSEReportGenerationService(ReportGenerationService):
  """SSE를 지원하는 보고서 생성 서비스"""
  
  def __init__(self):
    super().__init__()
    self.sse_service = SSEService()
  
  async def generate_report_with_sse(self,
      company_name: str,
      credit_rating_result: Dict[str, Any],
      financial_data: Dict[str, Any],
      report_type: str = "standard") -> AsyncGenerator:
    """
    신용등급 결과와 재무제표 데이터를 기반으로 보고서를 생성하고 진행 상황을 SSE로 전송합니다.
    
    Args:
        company_name: 회사명
        credit_rating_result: 신용등급 평가 결과
        financial_data: 재무제표 데이터
        report_type: 보고서 유형 (기본값: "standard")
        
    Returns:
        AsyncGenerator: SSE 이벤트 생성기
    """
    try:
      # 보고서 생성 시작 이벤트
      yield self.sse_service._format_event(
        event="message",
        data={
          "step": ProcessStep.REPORT_GENERATION_STARTED,
          "message": f"{company_name} 기업의 보고서 생성을 시작합니다.",
          "progress": 10
        }
      )
      await asyncio.sleep(0.1)
      
      # 데이터 전처리
      yield self.sse_service._format_event(
        event="message",
        data={
          "step": ProcessStep.REPORT_GENERATION_PROCESSING,
          "message": "보고서 생성을 위한 데이터 준비 중...",
          "progress": 20
        }
      )
      await asyncio.sleep(0.1)
      
      # 에이전트 기반 보고서 생성 시작
      yield self.sse_service._format_event(
        event="message",
        data={
          "step": ProcessStep.REPORT_GENERATION_PROCESSING,
          "message": "AI 에이전트를 통한 보고서 생성 중...",
          "progress": 40
        }
      )
      await asyncio.sleep(0.1)
      
      # 에이전트 기반 보고서 생성 (진행 상황 업데이트 콜백 포함)
      report_result = await self._generate_agent_based_report_with_progress(
        company_name,
        credit_rating_result,
        financial_data,
        lambda message, progress: self._report_progress_callback(message, progress)
      )
      
      # 보고서 생성 완료 이벤트
      yield self.sse_service._format_event(
        event="message",
        data={
          "step": ProcessStep.REPORT_GENERATION_COMPLETED,
          "message": f"{company_name} 기업의 보고서 생성이 완료되었습니다.\n잠시만 기다려주세요.",
          "progress": 100,
          "result": report_result
        }
      )
    
    except Exception as e:
      logger.error(f"보고서 생성 중 오류 발생: {str(e)}")
      # 오류 이벤트 전송
      yield self.sse_service._format_event(
        event="error",
        data={
          "step": ProcessStep.ERROR,
          "message": f"보고서 생성 중 오류가 발생했습니다: {str(e)}",
          "error": str(e)
        }
      )
      raise ValueError(f"보고서 생성 중 오류 발생: {str(e)}")
  
  async def _generate_agent_based_report_with_progress(self,
      company_name: str,
      credit_rating_result: Dict[str, Any],
      financial_data: Dict[str, Any],
      progress_callback: Optional[Callable[[str, int], None]] = None) -> Dict[str, Any]:
    """
    에이전트를 사용하여 보고서를 생성하고 진행 상황을 콜백으로 전달합니다.
    
    Args:
        company_name: 회사명
        credit_rating_result: 신용등급 평가 결과
        financial_data: 재무제표 데이터
        progress_callback: 진행 상황 콜백 함수
        
    Returns:
        Dict[str, Any]: 생성된 보고서 내용
    """
    # 에이전트 초기화
    agent = self.report_agent
    
    # 보고서 생성 시작
    if progress_callback:
      progress_callback("보고서 생성을 위한 데이터 분석 중...", 50)
    
    # 관련 뉴스 데이터 가져오기
    from app.domain.report_generation.news_utils import fetch_latest_news_links
    try:
        news_data = fetch_latest_news_links(company_name, max_results=3)
        logger.info(f"{company_name}에 대한 뉴스 {len(news_data)}개 가져오기 성공")
    except Exception as e:
        logger.error(f"뉴스 데이터 가져오기 실패: {str(e)}")
        news_data = []
    
    # 재무 데이터 및 신용등급 정보 포맷팅
    formatted_financial_data = self.report_agent._format_financial_data(financial_data)
    formatted_credit_rating = self.report_agent._format_credit_rating(credit_rating_result)
    
    if progress_callback:
      progress_callback("보고서 초안 작성 중...", 70)
    
    # 에이전트를 통한 보고서 생성
    report_result = await agent.generate_report(
      company_name=company_name,
      financial_data=financial_data,
      credit_rating_result=credit_rating_result
    )
    
    if progress_callback:
      progress_callback("보고서 최종 검토 및 포맷팅 중...", 90)
    
    # 보고서 결과에 뉴스 데이터 추가
    # 기존 report_result가 문자열이 아닌 딕셔너리인지 확인
    if isinstance(report_result, dict):
        report_result["news_data"] = news_data
    else:
        # 문자열이면 딕셔너리로 변환하여 뉴스 데이터 추가
        report_result = {
            "report_content": report_result,
            "news_data": news_data
        }
    
    # 디버깅을 위해 로그 추가
    logger.info(f"보고서 결과에 뉴스 데이터 추가 완료: {len(news_data)}개 뉴스")
    
    return report_result
  
  def _report_progress_callback(self, message: str, progress: int):
    """
    보고서 생성 진행 상황 콜백 함수
    
    Args:
        message: 진행 상황 메시지
        progress: 진행률 (0-100)
    """
    # 이 메서드는 실제 SSE 이벤트를 생성하지 않고 로깅만 수행합니다.
    # 실제 SSE 이벤트는 generate_report_with_sse 메서드에서 yield 됩니다.
    logger.info(f"보고서 생성 진행 상황: {message} ({progress}%)")
