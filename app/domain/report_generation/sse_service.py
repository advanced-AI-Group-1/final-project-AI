"""
SSE를 지원하는 보고서 생성 서비스
"""
import asyncio
import logging
from typing import Dict, Any, AsyncGenerator, Optional, Callable, List

from app.domain.report_generation.service import ReportGenerationService
from app.domain.report_generation.agent import SSEReportAgent
from app.domain.sse.service import SSEService, ProcessStep

logger = logging.getLogger(__name__)


class SSEReportGenerationService(ReportGenerationService):
  """SSE를 지원하는 보고서 생성 서비스"""
  
  def __init__(self):
    super().__init__()
    self.sse_service = SSEService()
    # SSEReportAgent 초기화
    self.report_agent = SSEReportAgent()
  
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
    # 이벤트 큐 생성
    event_queue = asyncio.Queue()
    
    # 이벤트 생성 함수
    def create_event(step, message, progress, result=None, error=None):
      data = {
        "step": step,
        "message": message,
        "progress": progress
      }
      if result:
        data["result"] = result
      if error:
        data["error"] = error
      
      return self.sse_service._format_event(
        event="message" if not error else "error",
        data=data
      )
    
    # 이벤트 전송 함수
    async def send_event(step, message, progress, result=None, error=None):
      event = create_event(step, message, progress, result, error)
      await event_queue.put(event)
    
    # 진행 상황 콜백 함수
    def progress_callback(message, progress):
      # 로깅 수행
      logger.info(f"보고서 생성 진행 상황: {message} ({progress}%)")
      # 이벤트 큐에 추가
      asyncio.create_task(send_event(
        ProcessStep.REPORT_GENERATION_PROCESSING,
        message,
        progress
      ))
    
    # 이벤트 처리 태스크
    async def event_processor():
      try:
        # 보고서 생성 시작 이벤트
        await send_event(
          ProcessStep.REPORT_GENERATION_STARTED,
          f"{company_name} 기업의 보고서 생성을 시작합니다.",
          10
        )
        
        # 데이터 전처리 이벤트
        await send_event(
          ProcessStep.REPORT_GENERATION_PROCESSING,
          "보고서 생성을 위한 데이터 준비 중...",
          20
        )
        
        # SSEReportAgent에 콜백 설정
        self.report_agent.set_progress_callback(progress_callback)
        
        try:
          # 에이전트 기반 보고서 생성
          report_result = await self.report_agent.generate_report(
            company_name=company_name,
            credit_rating_result=credit_rating_result,
            financial_data=financial_data
          )
          
          # 보고서 생성 완료 이벤트
          await send_event(
            ProcessStep.REPORT_GENERATION_COMPLETED,
            f"{company_name} 기업의 보고서 생성이 완료되었습니다.",
            100,
            result=report_result
          )
        except Exception as e:
          logger.error(f"보고서 생성 중 오류 발생: {str(e)}")
          # 오류 이벤트 전송
          await send_event(
            ProcessStep.ERROR,
            f"보고서 생성 중 오류가 발생했습니다: {str(e)}",
            0,
            error=str(e)
          )
          raise
        finally:
          # 이벤트 큐에 종료 신호 추가
          await event_queue.put(None)
      except Exception as e:
        logger.error(f"이벤트 처리 중 오류 발생: {str(e)}")
        # 이벤트 큐에 종료 신호 추가
        await event_queue.put(None)
        raise
    
    # 이벤트 처리 태스크 시작
    asyncio.create_task(event_processor())
    
    # 이벤트 큐에서 이벤트를 가져와 yield
    while True:
      event = await event_queue.get()
      if event is None:  # 종료 신호
        event_queue.task_done()
        break
      
      yield event
      event_queue.task_done()
