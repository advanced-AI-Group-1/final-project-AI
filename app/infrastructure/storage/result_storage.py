"""
비동기 작업 결과를 저장하고 조회하기 위한 저장소
"""
from typing import Dict, Any, Optional
import time
from datetime import datetime, timedelta


class ResultStorage:
  """
    비동기 작업 결과를 저장하고 조회하기 위한 인메모리 저장소
    """
  _instance = None

  def __new__(cls):
    if cls._instance is None:
      cls._instance = super(ResultStorage, cls).__new__(cls)
      cls._instance._results = {}  # 결과 저장 딕셔너리
      cls._instance._expiry_times = {}  # 결과 만료 시간 딕셔너리
      cls._instance._default_ttl = 3600  # 기본 TTL (1시간)
    return cls._instance

  def store_result(self, request_id: str, result: Dict[str, Any], ttl: int = None) -> None:
    """
        결과를 저장소에 저장합니다.
        
        Args:
            request_id (str): 요청 ID
            result (Dict[str, Any]): 저장할 결과
            ttl (int, optional): 결과 유효 시간(초). 기본값은 1시간.
        """
    self._results[request_id] = result
    expiry_time = datetime.now() + timedelta(seconds=ttl or self._default_ttl)
    self._expiry_times[request_id] = expiry_time

  def get_result(self, request_id: str) -> Optional[Dict[str, Any]]:
    """
        저장소에서 결과를 조회합니다.
        
        Args:
            request_id (str): 요청 ID
            
        Returns:
            Optional[Dict[str, Any]]: 저장된 결과 또는 None
        """
    # 만료된 결과 정리
    self._cleanup_expired()

    # 결과 반환
    return self._results.get(request_id)

  def store_status(self, request_id: str, status: str, message: str = None, ttl: int = None) -> None:
    """
        작업 상태를 저장합니다.
        
        Args:
            request_id (str): 요청 ID
            status (str): 상태 (예: "PENDING", "PROCESSING", "COMPLETED", "FAILED")
            message (str, optional): 상태 메시지
            ttl (int, optional): 결과 유효 시간(초). 기본값은 1시간.
        """
    result = {"status": status, "message": message, "timestamp": datetime.now().isoformat()}
    self.store_result(request_id, result, ttl)

  def _cleanup_expired(self) -> None:
    """
        만료된 결과를 정리합니다.
        """
    now = datetime.now()
    expired_ids = [request_id for request_id, expiry_time in self._expiry_times.items() if expiry_time < now]

    for request_id in expired_ids:
      if request_id in self._results:
        del self._results[request_id]
      if request_id in self._expiry_times:
        del self._expiry_times[request_id]
