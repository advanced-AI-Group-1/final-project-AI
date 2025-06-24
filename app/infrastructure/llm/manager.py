from typing import Dict, Any, Optional
import os
import openai
from openai import AsyncOpenAI
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class LLMManager:
    """
    LLM(Large Language Model) 호출을 관리하는 클래스
    """
    def __init__(self):
        # 환경 변수에서 OpenAI API 키 가져오기
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        # OpenAI 클라이언트 초기화
        self.client = AsyncOpenAI(api_key=self.api_key)
        
        # 환경 변수에서 모델 설정 가져오기
        self.default_model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4.1-mini")
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2000"))
        
    async def generate_response(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        LLM을 사용하여 프롬프트에 대한 응답을 생성합니다.
        
        Args:
            prompt (str): LLM에 전달할 프롬프트
            model (Optional[str]): 사용할 모델 (기본값: .env에서 설정한 값)
            temperature (float): 생성 다양성 조절 (0.0 ~ 1.0)
            max_tokens (int): 최대 생성 토큰 수
            
        Returns:
            str: LLM이 생성한 응답
        """
        try:
            # 사용할 모델 설정
            model_name = model or self.default_model
            temp = temperature if temperature is not None else self.temperature
            tokens = max_tokens or self.max_tokens
            
            # OpenAI API 호출
            response = await self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "당신은 금융 및 신용평가 전문가입니다. 정확하고 객관적인 분석을 제공합니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temp,
                max_tokens=tokens
            )
            
            # 응답 텍스트 추출
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"LLM 응답 생성 중 오류 발생: {str(e)}")
            return f"오류 발생: {str(e)}"
            
    async def generate_structured_response(
        self, 
        prompt: str, 
        output_schema: Dict[str, Any],
        model: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        구조화된 형식으로 LLM 응답을 생성합니다.
        
        Args:
            prompt (str): LLM에 전달할 프롬프트
            output_schema (Dict[str, Any]): 응답의 JSON 스키마
            model (Optional[str]): 사용할 모델
            temperature (float): 생성 다양성 조절
            
        Returns:
            Dict[str, Any]: 구조화된 LLM 응답
        """
        try:
            # 사용할 모델 설정
            model_name = model or self.default_model
            temp = temperature if temperature is not None else self.temperature
            
            # 스키마를 포함한 프롬프트 구성
            schema_prompt = f"""
            {prompt}
            
            다음 JSON 스키마에 맞게 응답해주세요:
            {output_schema}
            
            응답은 반드시 유효한 JSON 형식이어야 합니다.
            """
            
            # OpenAI API 호출
            response = await self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "당신은 금융 및 신용평가 전문가입니다. 정확하고 객관적인 분석을 제공합니다."},
                    {"role": "user", "content": schema_prompt}
                ],
                temperature=temp,
                response_format={"type": "json_object"}
            )
            
            # JSON 응답 파싱
            import json
            response_text = response.choices[0].message.content
            return json.loads(response_text)
            
        except Exception as e:
            print(f"구조화된 LLM 응답 생성 중 오류 발생: {str(e)}")
            return {"error": str(e)}
