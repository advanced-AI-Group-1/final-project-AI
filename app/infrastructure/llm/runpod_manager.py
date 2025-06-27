from typing import Dict, Any, Optional
import os
import json
import time
import aiohttp
import asyncio
from fastapi import HTTPException, BackgroundTasks
from app.infrastructure.storage.result_storage import ResultStorage
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class RunPodLLMManager:
  """
    RunPod API를 통해 LLM(Large Language Model) 호출을 관리하는 클래스
    """

  def __init__(self):
    # 환경 변수에서 RunPod API 키 가져오기
    self.api_key = os.getenv("RUNPOD_API_KEY")
    if not self.api_key:
      raise ValueError("RUNPOD_API_KEY 환경 변수가 설정되지 않았습니다.")

    # 환경 변수에서 RunPod 엔드포인트 ID 가져오기
    self.endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID")
    if not self.endpoint_id:
      raise ValueError("RUNPOD_ENDPOINT_ID 환경 변수가 설정되지 않았습니다.")

    # RunPod 엔드포인트 설정
    self.base_url = f"https://api.runpod.ai/v2/{self.endpoint_id}"
    self.run_url = f"{self.base_url}/run"
    self.status_url = f"{self.base_url}/status"

    # 요청 헤더 설정
    self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    # 폴링 설정 - 더 긴 시간 동안 기다리도록 수정
    self.polling_interval = 3  # 초 단위 (2초에서 3초로 증가)
    self.max_polling_attempts = 100  # 최대 폴링 시도 횟수 (30에서 100으로 증가, 약 5분)

    # 결과 저장소 초기화
    self.result_storage = ResultStorage()

  def _format_alpaca_prompt(self, instruction: str, input_text: str) -> str:
    """
        Alpaca 형식으로 프롬프트를 포맷팅합니다.
        
        Args:
            instruction (str): 지시문
            input_text (str): 입력 텍스트
            
        Returns:
            str: Alpaca 형식의 프롬프트
        """
    from app.infrastructure.llm.prompt_templates import ALPACA_PROMPT_TEMPLATE
    return ALPACA_PROMPT_TEMPLATE.format(instruction, input_text)

  async def _send_request(self, prompt: str) -> Dict[str, Any]:
    """
        RunPod API에 요청을 보냅니다.
        
        Args:
            prompt (str): LLM에 전달할 프롬프트
            
        Returns:
            Dict[str, Any]: 요청 ID를 포함한 응답
        """
    payload = {"input": {"prompt": prompt}}

    async with aiohttp.ClientSession() as session:
      async with session.post(self.run_url, headers=self.headers, json=payload) as response:
        if response.status != 200:
          error_text = await response.text()
          raise HTTPException(status_code=response.status, detail=f"RunPod API 요청 실패: {error_text}")

        result = await response.json()
        return result

  async def _check_status(self, request_id: str) -> Dict[str, Any]:
    """
        RunPod API 요청의 상태를 확인합니다.
        
        Args:
            request_id (str): 요청 ID
            
        Returns:
            Dict[str, Any]: 요청 결과
        """
    status_url = f"{self.status_url}/{request_id}"

    async with aiohttp.ClientSession() as session:
      async with session.get(status_url, headers=self.headers) as response:
        if response.status != 200:
          error_text = await response.text()
          raise HTTPException(status_code=response.status, detail=f"RunPod 상태 확인 실패: {error_text}")

        result = await response.json()
        return result

  async def _poll_for_result(self, request_id: str) -> Dict[str, Any]:
    """
        결과가 준비될 때까지 RunPod API를 폴링합니다.
        
        Args:
            request_id (str): 요청 ID
            
        Returns:
            Dict[str, Any]: 요청 결과
        """
    for attempt in range(self.max_polling_attempts):
      result = await self._check_status(request_id)
      status = result.get("status")

      if status == "COMPLETED":
        return result
      elif status in ["FAILED", "CANCELLED"]:
        raise HTTPException(status_code=500, detail=f"RunPod 요청 실패: {result}")

      # 현재 상태 로깅
      print(f"RunPod 요청 상태 ({attempt+1}/{self.max_polling_attempts}): {status}")

      # 다음 폴링 전 대기
      await asyncio.sleep(self.polling_interval)

    raise HTTPException(status_code=504, detail="RunPod 요청 시간 초과")

  async def generate_response(self, instruction: str, input_text: str) -> str:
    """
        RunPod API를 통해 LLM 응답을 생성합니다.
        
        Args:
            instruction (str): 지시문
            input_text (str): 입력 텍스트
            
        Returns:
            str: LLM이 생성한 응답
        """
    try:
      # Alpaca 형식으로 프롬프트 포맷팅
      prompt = self._format_alpaca_prompt(instruction, input_text)

      # RunPod API에 요청 보내기
      request_result = await self._send_request(prompt)
      request_id = request_result.get("id")

      if not request_id:
        raise HTTPException(status_code=500, detail="RunPod 요청 ID를 받지 못했습니다.")

      # 결과 폴링
      result = await self._poll_for_result(request_id)

      # 응답 추출
      output = result.get("output", [])
      if not output or not isinstance(output, list) or len(output) == 0:
        raise HTTPException(status_code=500, detail="RunPod 응답에서 출력을 찾을 수 없습니다.")

      choices = output[0].get("choices", [])
      if not choices or len(choices) == 0:
        raise HTTPException(status_code=500, detail="RunPod 응답에서 선택 항목을 찾을 수 없습니다.")

      tokens = choices[0].get("tokens", [])
      if not tokens or len(tokens) == 0:
        raise HTTPException(status_code=500, detail="RunPod 응답에서 토큰을 찾을 수 없습니다.")

      # 첫 번째 토큰이 응답 텍스트
      return tokens[0]

    except Exception as e:
      print(f"RunPod LLM 응답 생성 중 오류 발생: {str(e)}")
      raise HTTPException(status_code=500, detail=f"RunPod LLM 오류: {str(e)}")

  async def submit_request(self, instruction: str, input_text: str) -> str:
    """
    RunPod API에 요청을 제출하고 요청 ID를 반환합니다.
    
    Args:
        instruction (str): 지시문
        input_text (str): 입력 텍스트
        
    Returns:
        str: 요청 ID
    """
    try:
      # Alpaca 형식으로 프롬프트 포맷팅
      prompt = self._format_alpaca_prompt(instruction, input_text)

      # RunPod API에 요청 보내기
      request_result = await self._send_request(prompt)
      request_id = request_result.get("id")

      if not request_id:
        raise HTTPException(status_code=500, detail="RunPod 요청 ID를 받지 못했습니다.")

      # 초기 상태 저장
      self.result_storage.store_status(request_id, "PENDING", "요청이 큐에 추가되었습니다.")

      return request_id

    except Exception as e:
      print(f"RunPod LLM 요청 제출 중 오류 발생: {str(e)}")
      raise HTTPException(status_code=500, detail=f"RunPod LLM 오류: {str(e)}")

  async def request(self, prompt: str) -> str:
    """
    프롬프트를 받아 RunPod API를 통해 LLM 응답을 생성합니다.
    
    Args:
        prompt (str): 프롬프트 텍스트
        
    Returns:
        str: LLM이 생성한 응답
    """
    try:
      # RunPod API에 요청 보내기
      request_result = await self._send_request(prompt)
      request_id = request_result.get("id")

      if not request_id:
        raise HTTPException(status_code=500, detail="RunPod 요청 ID를 받지 못했습니다.")

      # 결과 폴링
      result = await self._poll_for_result(request_id)

      # 응답 추출
      output = result.get("output", [])
      if not output or not isinstance(output, list) or len(output) == 0:
        raise HTTPException(status_code=500, detail="RunPod 응답에서 출력을 찾을 수 없습니다.")

      choices = output[0].get("choices", [])
      if not choices or len(choices) == 0:
        raise HTTPException(status_code=500, detail="RunPod 응답에서 선택 항목을 찾을 수 없습니다.")

      tokens = choices[0].get("tokens", [])
      if not tokens or len(tokens) == 0:
        raise HTTPException(status_code=500, detail="RunPod 응답에서 토큰을 찾을 수 없습니다.")

      # 첫 번째 토큰이 응답 텍스트
      return tokens[0]

    except Exception as e:
      print(f"RunPod LLM 응답 생성 중 오류 발생: {str(e)}")
      raise HTTPException(status_code=500, detail=f"RunPod LLM 오류: {str(e)}")

  async def process_request_background(self, request_id: str, company_name: str, financial_data: Dict[str,
                                                                                                    Any]) -> None:
    """
    백그라운드에서 RunPod API 요청을 처리합니다.
    
    Args:
        request_id (str): 요청 ID
        company_name (str): 회사명
        financial_data (Dict[str, Any]): 재무 데이터
    """
    try:
      # 상태 업데이트
      self.result_storage.store_status(request_id, "PROCESSING", "요청을 처리 중입니다.")

      # 결과 폴링
      result = await self._poll_for_result(request_id)

      # 응답 추출
      output = result.get("output", [])
      if not output or not isinstance(output, list) or len(output) == 0:
        self.result_storage.store_status(request_id, "FAILED", "RunPod 응답에서 출력을 찾을 수 없습니다.")
        return

      choices = output[0].get("choices", [])
      if not choices or len(choices) == 0:
        self.result_storage.store_status(request_id, "FAILED", "RunPod 응답에서 선택 항목을 찾을 수 없습니다.")
        return

      tokens = choices[0].get("tokens", [])
      if not tokens or len(tokens) == 0:
        self.result_storage.store_status(request_id, "FAILED", "RunPod 응답에서 토큰을 찾을 수 없습니다.")
        return

      # 응답 텍스트 추출
      response_text = tokens[0]

      # 신용등급 결과 파싱
      try:
        # CreditRatingService의 파싱 메서드 사용
        from app.domain.credit_rating.service import CreditRatingService
        credit_rating_service = CreditRatingService()
        credit_rating_result = credit_rating_service._parse_credit_rating_response(response_text, company_name)

        # 결과 저장
        self.result_storage.store_result(request_id, {
            "status": "COMPLETED",
            "result": credit_rating_result,
            "timestamp": time.time()
        })

      except Exception as e:
        print(f"응답 파싱 중 오류 발생: {str(e)}")
        self.result_storage.store_status(request_id, "FAILED", f"응답 파싱 중 오류 발생: {str(e)}")

    except Exception as e:
      print(f"백그라운드 처리 중 오류 발생: {str(e)}")
      self.result_storage.store_status(request_id, "FAILED", f"처리 중 오류 발생: {str(e)}")

  def get_request_status(self, request_id: str) -> Dict[str, Any]:
    """
    요청 상태를 조회합니다.
    
    Args:
        request_id (str): 요청 ID
        
    Returns:
        Dict[str, Any]: 요청 상태 및 결과
    """
    result = self.result_storage.get_result(request_id)
    if not result:
      raise HTTPException(status_code=404, detail=f"요청 ID {request_id}에 대한 결과를 찾을 수 없습니다.")

    return result
