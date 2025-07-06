"""
SSE(Server-Sent Events) 서비스 구현
"""
import asyncio
import json
import logging
from enum import Enum
from typing import Dict, Any, AsyncGenerator, Optional, Callable

from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger(__name__)


class ProcessStep(str, Enum):
  """처리 단계를 나타내는 열거형"""
  STARTED = "started"
  CREDIT_RATING_STARTED = "credit_rating_started"
  CREDIT_RATING_PROCESSING = "credit_rating_processing"
  CREDIT_RATING_COMPLETED = "credit_rating_completed"
  REPORT_GENERATION_STARTED = "report_generation_started"
  REPORT_GENERATION_PROCESSING = "report_generation_processing"
  REPORT_GENERATION_COMPLETED = "report_generation_completed"
  COMPLETED = "completed"
  ERROR = "error"


# 완료된 단계 목록 정의
COMPLETED_STEPS = [
  # ProcessStep.COMPLETED,
  # ProcessStep.CREDIT_RATING_COMPLETED,
  ProcessStep.REPORT_GENERATION_COMPLETED,
]


class SSEService:
  """SSE 이벤트를 생성하는 서비스"""
  
  def __init__(self):
    self.logger = logging.getLogger(__name__)
  
  async def generate_events(self,
      process_func: Callable,
      process_args: Dict[str, Any],
      progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None) -> AsyncGenerator:
    """
    처리 과정에서 SSE 이벤트를 생성합니다.
    
    Args:
        process_func: 실행할 처리 함수
        process_args: 처리 함수에 전달할 인자
        progress_callback: 진행 상황 콜백 함수
        
    Returns:
        AsyncGenerator: SSE 이벤트 생성기
    """
    try:
      # 시작 이벤트 전송
      yield self._format_event(
        event="message",
        data={
          "step": ProcessStep.STARTED,
          "message": "처리를 시작합니다.",
          "progress": 0
        }
      )
      await asyncio.sleep(0.1)
      
      # 처리 함수 실행 (결과는 마지막에 반환)
      result = await process_func(**process_args)
      
      # 완료 이벤트 전송
      yield self._format_event(
        event="message",
        data={
          "step": ProcessStep.COMPLETED,
          "message": "처리가 완료되었습니다.",
          "progress": 100,
          "result": result
        }
      )
    
    except Exception as e:
      self.logger.error(f"SSE 이벤트 생성 중 오류 발생: {str(e)}")
      # 오류 이벤트 전송
      yield self._format_event(
        event="error",
        data={
          "step": ProcessStep.ERROR,
          "message": f"처리 중 오류가 발생했습니다: {str(e)}",
          "error": str(e)
        }
      )
  
  def _format_event(self, event: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    SSE 이벤트 형식으로 데이터를 포맷팅합니다.
    
    Args:
        event: 이벤트 유형
        data: 이벤트 데이터
        
    Returns:
        Dict[str, Any]: 포맷팅된 이벤트
    """
    # 완료 상태 필드 추가
    if "step" in data and isinstance(data["step"], ProcessStep):
      data["is_completed"] = data["step"] in COMPLETED_STEPS
    
    return {
      "event": event,
      "data": json.dumps(data, ensure_ascii=False)
    }
  
  def create_sse_response(self, generator: AsyncGenerator) -> EventSourceResponse:
    """
    SSE 응답 객체를 생성합니다.
    
    Args:
        generator: 이벤트 생성기
        
    Returns:
        EventSourceResponse: SSE 응답 객체
    """
    return EventSourceResponse(generator)
