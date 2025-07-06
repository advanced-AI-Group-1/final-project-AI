"""
LangGraph를 사용한 보고서 생성 에이전트 구현
"""
import logging
import os
import re
import time
import traceback
from datetime import datetime
from typing import Dict, Any

from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from tavily import TavilyClient

from app.domain.report_generation.models import ReportState, \
  AdditionalRatioCalculator, Section
from app.domain.report_generation.prompts import (SUMMARY_CARD_PROMPT,
                                                  FINANCIAL_ANALYSIS_PROMPT,
                                                  CREDIT_RATING_ANALYSIS_PROMPT,
                                                  CONCLUSION_PROMPT)
from app.infrastructure.llm.manager import LLMManager
from app.utils.logging_utils import log_to_memory, log_node_to_memory


class ReportAgent:
  """
    LangGraph를 사용한 보고서 생성 에이전트
    """
  
  def __init__(self):
    self.llm_manager = LLMManager()
    # 섹션 품질 점수 임계값 설정 (이 점수 미만이면 재생성)
    self.quality_threshold = 7.0
    # 로거 설정
    self.logger = logging.getLogger(__name__)
    self.logger.setLevel(logging.INFO)
    
    # LLM 모델 정보 로깅
    self.logger.info("ReportAgent 초기화 중...")
    self.logger.info(f"사용 중인 LLM 모델: {self.llm_manager.default_model}")
    self.logger.info(f"LLM 온도(temperature) 설정: {self.llm_manager.temperature}")
    self.logger.info(f"최대 토큰 수: {self.llm_manager.max_tokens}")
  
  async def _call_llm(self, prompt: str, section_name: str = "", company_name: str = "") -> str:
    """
    LLM을 호출하여 응답을 생성합니다.

    Args:
        prompt (str): LLM에 전달할 프롬프트
        section_name (str, optional): 섹션 이름 (로깅용)
        company_name (str, optional): 회사명 (로깅용)

    Returns:
        str: LLM 응답
    """
    # 회사명이 제공된 경우에만 로깅
    if company_name:
      # 프롬프트 로깅
      prefix = f"section_{section_name}" if section_name else "general"
      log_to_memory(prompt, 'prompt', 'report_agent', company_name, '원', prefix)
    
    # LLM 호출
    response = await self.llm_manager.generate_response(prompt)
    
    # 회사명이 제공된 경우에만 로깅
    if company_name:
      # 응답 로깅
      prefix = f"section_{section_name}" if section_name else "general"
      log_to_memory(response, 'response', 'report_agent', company_name, '원', prefix)
    
    return response
  
  def _format_financial_data(self, financial_data: Dict[str, Any]) -> str:
    """재무 데이터를 문자열로 포맷팅합니다."""
    result = []
    
    # 기본 정보
    result.append(f"기업명: {financial_data.get('corp_name', '')}")
    result.append(f"업종: {financial_data.get('industry_name', '')}")
    result.append(f"시장구분: {financial_data.get('market_type', '')}")
    
    # 손익계산서
    result.append("\n■ 손익계산서 데이터:")
    result.append(f"매출액: {financial_data.get('revenue', 0):,.0f}원")
    result.append(
      f"영업이익: {financial_data.get('operating_profit', 0):,.0f}원 (이익률: {financial_data.get('operating_profit', 0) / financial_data.get('revenue', 1) * 100:.2f}%)"
    )
    result.append(
      f"당기순이익: {financial_data.get('net_income', 0):,.0f}원 (이익률: {financial_data.get('net_income', 0) / financial_data.get('revenue', 1) * 100:.2f}%)"
    )
    
    # 재무상태표
    result.append("\n■ 재무상태표 데이터:")
    result.append(f"총자산: {financial_data.get('total_assets', 0):,.0f}원")
    result.append(f"총부채: {financial_data.get('total_liabilities', 0):,.0f}원")
    result.append(f"자본총계: {financial_data.get('total_equity', 0):,.0f}원")
    
    # 현금흐름표
    result.append("\n■ 현금흐름표 데이터:")
    operating_cf_keys = ['operating_cash_flow', '영업활동현금흐름', 'cash_flow_from_operation']
    for key in operating_cf_keys:
      if key in financial_data and financial_data[key] is not None:
        result.append(f"영업활동현금흐름: {financial_data.get(key, 0):,.0f}원")
        break
    if 'interest_expense' in financial_data:
      result.append(f"이자비용: {financial_data.get('interest_expense', 0):,.0f}원")
    if 'ebitda' in financial_data:
      result.append(f"EBITDA: {financial_data.get('ebitda', 0):,.0f}원")
    
    # 주요 재무비율
    result.append("\n■ 주요 재무비율 데이터:")
    
    # 부채비율 - 자본잠식 상태(자본총계가 음수)인 경우 특별 처리
    if financial_data.get('total_equity', 0) <= 0:
      result.append("부채비율: 자본잠식 상태 (자본총계가 음수이므로 부채비율을 계산할 수 없음)")
    else:
      result.append(f"부채비율: {financial_data.get('debt_ratio', 0) * 100:.2f}%")
    
    result.append(f"ROA(총자산이익률): {financial_data.get('ROA', 0) * 100:.2f}%")
    
    # ROE - 자본잠식 상태인 경우 특별 처리
    if financial_data.get('total_equity', 0) <= 0:
      result.append("ROE(자기자본이익률): 자본잠식 상태 (자본총계가 음수이므로 해석에 주의 필요)")
    else:
      result.append(f"ROE(자기자본이익률): {financial_data.get('ROE', 0) * 100:.2f}%")
    
    result.append(f"매출총자산회전율: {financial_data.get('asset_turnover_ratio', 0):.2f}회")
    
    # 단위 변환 가이드 및 강력한 지침 추가
    result.append("\n■ 단위 표기 규칙 (반드시 준수):")
    result.append("- 위 데이터는 모두 '원' 단위로 제공됩니다")
    result.append("- 보고서 작성 시 가독성을 위해 다음 규칙을 따르세요:")
    result.append("  1. 1조원 이상: 조원 단위 사용 (예: 877,281,800,000,000원 → 877.3조원)")
    result.append("  2. 1,000억원 이상: 조원 단위 사용 (예: 341,968,000,000원 → 0.34조원)")
    result.append("  3. 1억원 이상: 억원 단위 사용 (예: 50,000,000,000원 → 500억원)")
    result.append("  4. 단위 변환 공식: 1조원 = 1,000,000,000,000원, 1억원 = 100,000,000원")
    result.append("- 절대 단위를 섞어서 쓰지 마세요 (일관성 유지)")
    result.append("- 예시: 매출액 877,281,800,000,000원은 반드시 '877.3조원'으로 표기")
    
    return "\n".join(result)
  
  def _format_credit_rating(self, credit_rating: Dict[str, Any]) -> str:
    """신용등급 정보를 문자열로 포맷팅합니다."""
    result = []
    
    result.append(f"신용등급: {credit_rating.get('credit_rating', 'N/A')}")
    
    # rating_details가 있는 경우에만 처리
    if credit_rating and 'rating_details' in credit_rating and credit_rating['rating_details']:
      details = credit_rating['rating_details']
      result.append("\n[등급 상세]")
      for key, value in details.items():
        # key를 한글로 변환
        if key == 'financial_strength':
          key_kr = '재무 건전성'
        elif key == 'business_risk':
          key_kr = '사업 위험'
        elif key == 'industry_outlook':
          key_kr = '산업 전망'
        else:
          key_kr = key
        
        result.append(f"{key_kr}: {value}")
    
    # 긍정적 요인이 있는 경우 처리
    if credit_rating and 'positive_factors' in credit_rating and credit_rating['positive_factors']:
      result.append("\n[긍정적 요인]")
      for factor in credit_rating['positive_factors']:
        result.append(f"- {factor}")
    
    # 부정적 요인이 있는 경우 처리
    if credit_rating and 'negative_factors' in credit_rating and credit_rating['negative_factors']:
      result.append("\n[부정적 요인]")
      for factor in credit_rating['negative_factors']:
        result.append(f"- {factor}")
    
    # confidence_score가 있는 경우에만 처리
    if credit_rating and 'confidence_score' in credit_rating:
      result.append(f"\n신뢰도 점수: {credit_rating.get('confidence_score', 0) * 100:.1f}%")
    
    return "\n".join(result)
  
  def _format_additional_ratios(self, ratios: Dict[str, float]) -> str:
    """추가 계산된 재무비율을 문자열로 포맷팅합니다."""
    result = []
    
    result.append("[추가 계산된 재무비율]")
    
    # 유동성 비율
    if 'estimated_current_ratio' in ratios:
      result.append(f"추정 유동비율: {ratios['estimated_current_ratio']:.2f}배")
    if 'cash_flow_ratio' in ratios:
      result.append(f"현금흐름비율: {ratios['cash_flow_ratio']:.2f}배")
    
    # 커버리지 비율
    if 'interest_coverage_ratio' in ratios:
      result.append(f"이자보상배율: {ratios['interest_coverage_ratio']:.2f}배")
    if 'ebitda_interest_coverage' in ratios:
      result.append(f"EBITDA 이자보상배율: {ratios['ebitda_interest_coverage']:.2f}배")
    if 'cash_interest_coverage' in ratios:
      result.append(f"현금흐름 이자보상배율: {ratios['cash_interest_coverage']:.2f}배")
    
    return "\n".join(result)
  
  def _initialize_state(self, company_name: str, credit_rating_result: Dict[str, Any],
      financial_data: Dict[str, Any]) -> ReportState:
    """초기 상태를 생성합니다."""
    # 섹션 초기화는 plan_sections 노드에서 수행하므로 빈 리스트로 설정
    return ReportState(company_data=financial_data,
      credit_rating=credit_rating_result,
      sections=[],
      current_section_index=0,
      all_analysis_done=False)
  
  async def _calculate_additional_ratios(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """추가 재무비율을 계산합니다."""
    self.logger.info("현재 노드: calculate_ratios")
    company_data = state["company_data"]
    
    # 추가 재무비율 계산
    additional_ratios = AdditionalRatioCalculator.calculate_all_additional_ratios(company_data)
    
    # 상태 업데이트
    state["additional_ratios"] = additional_ratios
    
    # 노드 결과 로깅
    company_name = company_data.get("corp_name", "")
    if company_name:
      # 로그 내용 구성
      log_content = "## 추가 재무비율 계산 결과\n\n"
      log_content += self._format_additional_ratios(additional_ratios)
      
      # 노드 결과를 메모리에 저장
      log_node_to_memory("calculate_ratios", log_content, "report_agent", company_name)
    
    return state
  
  async def _generate_summary_card(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """요약 카드를 생성합니다."""
    self.logger.info("현재 노드: generate_summary")
    company_data = state["company_data"]
    credit_rating = state["credit_rating"]
    
    # 프롬프트 구성
    prompt = SUMMARY_CARD_PROMPT.format(company_name=company_data.get("corp_name", ""),
      industry_name=company_data.get("industry_name", ""),
      market_type=company_data.get("market_type", ""),
      financial_data=self._format_financial_data(company_data),
      credit_rating=self._format_credit_rating(credit_rating),
      evaluation_date=datetime.now().strftime("%Y년 %m월 %d일"))
    
    # LLM 호출
    summary_card = await self._call_llm(prompt, section_name="요약 카드",
      company_name=company_data.get("corp_name", ""))
    
    # 구조화된 데이터 추출을 위한 프롬프트 구성
    structured_prompt = """
    다음 요약 카드에서 정보를 추출하여 JSON 형식으로 반환해주세요:
    
    ```
    {summary_card}
    ```
    
    다음 형식으로 반환해주세요:
    ```json
    {{
      "company_name": "기업명",
      "evaluation_date": "평가일자",
      "credit_rating": "신용등급",
      "strengths": ["강점1", "강점2", "강점3"],
      "weaknesses": ["약점1", "약점2", "약점3"],
      "financial_metrics": {{
        "roa": {{"value": 0.0, "display_value": "0.00%", "evaluation": "평가", "color_grade": 1-5}},
        "roe": {{"value": 0.0, "display_value": "0.00%", "evaluation": "평가", "color_grade": 1-5}},
        "debt_ratio": {{"value": 0.0, "display_value": "0.00%", "evaluation": "평가", "color_grade": 1-5, "is_capital_impaired": false}},
        "operating_profit_margin": {{"value": 0.0, "display_value": "0.00%", "evaluation": "평가", "color_grade": 1-5}}
      }},
      "credit_rating_trend": {{
        "direction": "상향/유지/하향",
        "reason": "이유"
      }},
      "financial_stability": "Strong/Moderate/Weak",
      "business_risk": "Strong/Moderate/Weak",
      "industry_outlook": "Stable/Positive/Negative"
    }}
    ```
    
    중요: 모든 재무지표는 반드시 다음 규칙을 따라주세요:
    1. value 필드에는 소수점 형태의 원본 값을 저장 (예: 0.067)
    2. display_value 필드에는 퍼센트로 변환한 값을 문자열로 저장 (예: "6.70%")
    3. 모든 재무지표는 퍼센트(%) 형식으로 표시해야 함
    4. 매출총자산회전율(asset_turnover_ratio)도 퍼센트로 변환하여 표시 (예: 0.5회 → "50.00%")
    
    color_grade는 다음 기준으로 1-5 사이의 정수값을 할당해주세요:
    1: 매우 나쁨 (심각한 수준으로 업계 평균보다 낮음)
    2: 나쁨 (업계 평균보다 낮음)
    3: 보통 (업계 평균 수준)
    4: 좋음 (업계 평균보다 높음)
    5: 매우 좋음 (탁월한 수준으로 업계 평균보다 높음)
    
    단, 부채비율(debt_ratio)의 경우 낮을수록 좋으므로 반대로 적용해주세요:
    1: 매우 높은 부채비율 (위험 수준)
    5: 매우 낮은 부채비율 (안전한 수준)
    
    특별히 자본잠식 상태(자본총계가 음수)인 경우, debt_ratio의 is_capital_impaired를 true로 설정하고 evaluation에 "자본잠식 상태로 부채비율이 의미가 없음"이라고 명시해주세요. 이 경우 color_grade는 1로 설정하세요.
    
    JSON 형식만 반환하고, 다른 설명은 포함하지 마세요.
    """.format(summary_card=summary_card)
    
    # LLM 호출하여 구조화된 데이터 추출
    structured_data_str = await self._call_llm(structured_prompt, section_name="요약 카드 구조화",
      company_name=company_data.get("corp_name", ""))
    
    # JSON 문자열에서 실제 JSON 부분만 추출
    try:
      # JSON 부분만 추출하기 위한 정규식
      import re
      json_match = re.search(r'```json\s*([\s\S]*?)\s*```', structured_data_str)
      if json_match:
        json_str = json_match.group(1)
      else:
        json_str = structured_data_str
      
      # 추출된 문자열을 JSON으로 파싱
      import json
      structured_data = json.loads(json_str)
    except Exception as e:
      self.logger.error(f"구조화된 데이터 파싱 오류: {e}")
      structured_data = {}
    
    # 상태 업데이트
    state["summary_card"] = summary_card
    state["summary_card_structured"] = structured_data
    
    # 노드 결과 로깅
    company_name = company_data.get("corp_name", "")
    if company_name:
      # 로그 내용 구성
      log_content = "## 요약 카드 생성 결과\n\n"
      log_content += summary_card
      log_content += "\n\n### 구조화된 데이터\n```json\n"
      log_content += json.dumps(structured_data, ensure_ascii=False, indent=2)
      log_content += "\n```"
      
      # 노드 결과를 메모리에 저장
      log_node_to_memory("generate_summary", log_content, "report_agent", company_name)
    
    return state
  
  def _format_section(self, section: Section) -> str:
    """섹션을 문자열로 포맷팅합니다."""
    return f"{section.name} ({section.description}) - 계산 필요: {section.requires_calculation}, 연구 필요: {section.requires_research}"
  
  async def _perform_web_search(self, query: str) -> str:
    """Tavily API를 사용하여 웹 검색을 수행합니다."""
    try:
      load_dotenv()
      # 환경 변수에서 API 키 가져오기
      api_key = os.environ.get("TAVILY_API_KEY")
      if not api_key:
        self.logger.info("Tavily API 키가 설정되지 않았습니다. 웹 검색을 건너뜁니다.")
        return None
      
      # Tavily 클라이언트 초기화
      client = TavilyClient(api_key=api_key)
      
      # 검색 수행
      search_result = client.search(query=query,
        search_depth="advanced",
        max_results=3,
        include_answer=True,
        include_raw_content=False,
        include_images=False)
      
      # 결과 추출
      if search_result and "answer" in search_result:
        return search_result["answer"]
      
      # 답변이 없는 경우 컨텐츠에서 정보 추출
      if search_result and "results" in search_result:
        content = []
        for result in search_result["results"]:
          if "content" in result:
            content.append(f"- {result['content']}")
        
        if content:
          return "\n\n".join(content)
      
      return None
    except Exception as e:
      self.logger.error(f"웹 검색 중 오류 발생: {str(e)}")
      return None
  
  async def _analyze_section(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """현재 섹션을 분석하고 해당 섹션의 보고서를 작성합니다."""
    self.logger.info("현재 노드: analyze_section")
    company_data = state["company_data"]
    credit_rating = state["credit_rating"]
    sections = state["sections"]
    current_index = state["current_section_index"]
    additional_ratios = state.get("additional_ratios", {})
    regeneration_mode = state.get("regeneration_mode", False)
    
    if current_index >= len(sections):
      state["all_analysis_done"] = True
      # LangGraph 버전 호환성을 위해 다음 노드를 명시적으로 지정
      state["next"] = "review_report"
      return state
    
    current_section = sections[current_index]
    
    # 웹 검색이 필요한 섹션인지 확인
    web_search_result = None
    if current_section.get("requires_research", False):
      search_query = f"{company_data.get('corp_name', '')} {company_data.get('industry_name', '')} {current_section['name']}"
      web_search_result = await self._perform_web_search(search_query)
    
    # 섹션별 프롬프트 구성
    if current_section["name"] == "재무 분석":
      prompt = FINANCIAL_ANALYSIS_PROMPT.format(company_name=company_data.get("corp_name", ""),
        industry_name=company_data.get("industry_name", ""),
        market_type=company_data.get("market_type", ""),
        financial_data=self._format_financial_data(company_data),
        additional_ratios=self._format_additional_ratios(additional_ratios))
    elif current_section["name"] == "신용등급 평가":
      prompt = CREDIT_RATING_ANALYSIS_PROMPT.format(company_name=company_data.get("corp_name", ""),
        industry_name=company_data.get("industry_name", ""),
        market_type=company_data.get("market_type", ""),
        financial_data=self._format_financial_data(company_data),
        credit_rating=self._format_credit_rating(credit_rating))
    elif current_section["name"] == "유동성 분석":
      prompt = """
            기업명: {company_name}
            업종: {industry_name}
            시장구분: {market_type}

            다음 재무 데이터와 신용등급 정보를 바탕으로 유동성 분석 내용을 작성해주세요:

            재무 데이터:
            {financial_data}

            신용등급 정보:
            {credit_rating}

            다음 관점에서 분석해주세요:
            1. 현금흐름 분석 (영업활동현금흐름, 투자활동현금흐름, 재무활동현금흐름)
            2. 운전자본 및 유동성 상태
            3. 단기 지급능력 평가
            4. 현금 관리 효율성

            **단위 표기 규칙 (반드시 준수):**
            1. 1조원 이상: 조원 단위 사용 (예: 877.3조원)
            2. 1,000억원 이상: 조원 단위 사용 (예: 0.34조원)
            3. 1억원 이상: 억원 단위 사용 (예: 500억원)
            4. 절대 단위를 섞어서 쓰지 마세요 (일관성 유지)

            중요: 응답에 '유동성 분석'이나 '유동성 분석 섹션'과 같은 제목을 포함하지 마세요. 바로 내용을 시작해주세요.

            글자 수 제한: {char_limit}자 이내
            """.format(
        company_name=company_data.get('corp_name', ''),
        industry_name=company_data.get('industry_name', ''),
        market_type=company_data.get('market_type', ''),
        financial_data=self._format_financial_data(company_data),
        credit_rating=self._format_credit_rating(credit_rating),
        char_limit=current_section['char_limit']
      )
    elif current_section["name"] == "결론 및 제언":
      prompt = CONCLUSION_PROMPT.format(company_name=company_data.get("corp_name", ""),
        industry_name=company_data.get("industry_name", ""),
        market_type=company_data.get("market_type", ""),
        financial_data=self._format_financial_data(company_data),
        credit_rating=self._format_credit_rating(credit_rating))
    else:
      # 기본 프롬프트
      prompt = f"""
            기업명: {company_data.get('corp_name', '')}
            업종: {company_data.get('industry_name', '')}
            시장구분: {company_data.get('market_type', '')}
            
            다음 재무 데이터와 신용등급 정보를 바탕으로 분석 내용을 작성해주세요:
            
            재무 데이터:
            {self._format_financial_data(company_data)}
            
            신용등급 정보:
            {self._format_credit_rating(credit_rating)}
            
            섹션 정보:
            섹션 설명: {current_section['description']}
            
            중요: 응답에 '{current_section['name']}' 또는 '{current_section['name']} 섹션'과 같은 제목을 포함하지 마세요. 바로 내용을 시작해주세요.
            
            글자 수 제한: {current_section['char_limit']}자 이내
            """
    
    # 재생성 모드인 경우 이전 검토 결과와 개선점 추가
    if regeneration_mode and "review_results" in state:
      review_results = state["review_results"]
      for review in review_results:
        if review["section_index"] == current_index:
          prompt += f"""

          이전 섹션 내용에 대한 검토 결과:
          {review["review"]}
          
          위 검토 결과를 참고하여 섹션 내용을 개선해주세요. 특히 지적된 문제점을 해결하고 더 높은 품질의 내용을 작성해주세요.
          """
          break
    
    # 웹 검색 결과가 있는 경우 프롬프트에 추가
    if web_search_result:
      prompt += f"\n\n웹 검색 결과:\n{web_search_result}\n\n위 웹 검색 결과를 참고하여 분석을 더 풍부하게 해주세요."
    
    # LLM 호출
    section_content = await self._call_llm(prompt, section_name=current_section['name'],
      company_name=company_data.get("corp_name", ""))
    
    # 기업 개요 섹션에서는 뉴스 부분을 제거하고 별도로 저장
    if current_section["name"].replace(" ", "") == "기업개요":
      # 뉴스 데이터는 이미 service.py에서 별도로 가져와서 API 응답에 포함시키므로 여기서는 추가하지 않음
      pass
    
    # 섹션 내용 업데이트
    sections[current_index]["content"] = section_content
    
    # 노드 결과 로깅
    company_name = company_data.get("corp_name", "")
    if company_name:
      # 로그 내용 구성
      log_content = f"## 섹션 분석: {current_section['name']}\n\n"
      log_content += f"### 섹션 설명\n{current_section['description']}\n\n"
      log_content += f"### 분석 결과\n{section_content}\n\n"
      if web_search_result:
        log_content += f"### 웹 검색 결과\n{web_search_result}\n\n"
      
      # 노드 결과를 메모리에 저장
      log_node_to_memory(f"analyze_section_{current_section['name']}", log_content, "report_agent",
        company_name)
    
    # 재생성 모드인 경우
    if regeneration_mode:
      # 현재 섹션이 재생성 목록의 마지막이면 재생성 모드 종료
      sections_to_regenerate = state.get("sections_to_regenerate", [])
      if sections_to_regenerate and current_index == sections_to_regenerate[-1]:
        # 재생성 모드 종료하고 컴파일로 진행
        state["regeneration_mode"] = False
        state["next"] = "compile_report"
        return state
      
      # 다음 재생성 섹션으로 이동
      try:
        current_idx = sections_to_regenerate.index(current_index)
        if current_idx < len(sections_to_regenerate) - 1:
          state["current_section_index"] = sections_to_regenerate[current_idx + 1]
          state["next"] = "analyze_section"
          return state
      except ValueError:
        pass
        
        # 오류 발생 시 안전하게 컴파일로 진행
      state["regeneration_mode"] = False
      state["next"] = "compile_report"
      return state
    
    # 일반 모드에서 다음 섹션으로 이동
    state["current_section_index"] = current_index + 1
    
    # 모든 섹션이 완료되었는지 확인하여 다음 노드 결정
    if state["current_section_index"] >= len(sections):
      state["all_analysis_done"] = True
      state["next"] = "review_report"
    else:
      state["next"] = "analyze_section"
    
    return state
  
  async def _review_report(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """보고서의 품질을 검증하고 점수를 매깁니다."""
    self.logger.info("현재 노드: review_report")
    sections = state["sections"]
    company_data = state["company_data"]
    credit_rating = state["credit_rating"]
    
    review_results = []
    sections_to_regenerate = []
    
    # 각 섹션 검증
    for i, section in enumerate(sections):
      self.logger.info(f"섹션 '{section['name']}' 검증 중...")
      
      # 검증 프롬프트 구성
      prompt = f"""
      당신은 금융 보고서 품질 검증 전문가입니다. 다음 '{section['name']}' 섹션의 내용을 검토하고 품질을 평가해주세요.
      
      # 재무 데이터
      {self._format_financial_data(company_data)}
      
      # 신용등급 정보
      {self._format_credit_rating(credit_rating)}
      
      # 추가 재무비율
      {self._format_additional_ratios(company_data.get('additional_ratios', {}))}
      
      # 섹션 정보
      섹션 이름: {section['name']}
      섹션 설명: {section['description']}
      
      섹션 내용:
      ```
      {section['content']}
      ```
      
      다음 항목에 대해 1-10점 척도로 평가해주세요:
      1. 정확성: 내용이 재무 데이터와 일치하는가?
      2. 완전성: 섹션 설명에 맞게 모든 필요한 내용을 다루었는가?
      3. 논리성: 분석이 논리적으로 전개되는가?
      4. 가독성: 내용이 명확하고 이해하기 쉬운가?
      5. 통찰력: 단순한 사실 나열을 넘어 의미 있는 통찰을 제공하는가?
      
      종합 점수: (1-10)
      
      개선이 필요한 부분:
      1.
      2.
      3.
      
      중요: 종합점수는 반드시 1-10 사이의 숫자만 입력하고, "종합점수:" 다음에 바로 숫자가 오도록 해주세요.
      """
      
      # LLM 호출
      review_result = await self._call_llm(prompt, section_name=section['name'],
        company_name=company_data.get("corp_name", ""))
      self.logger.info(f"LLM 응답 (섹션 '{section['name']}'): {review_result[:100]}...")
      
      # 점수 추출
      score = None
      
      # 방법 1: '종합 점수:' 형식 찾기
      score_lines = [line for line in review_result.split('\n') if '종합' in line and '점수' in line]
      if score_lines:
        score_text = re.split(r'종합\s*점수:', score_lines[0], maxsplit=1)[1].strip()
        # 숫자만 추출
        score_match = re.search(r'(\d+(\.\d+)?)', score_text)
        if score_match:
          score = float(score_match.group(1))
          self.logger.info(f"방법 1로 점수 추출 성공: {score} (원본 텍스트: '{score_text}')")
          
          # 점수가 1-10 범위를 벗어나면 무효화
          if score < 1 or score > 10:
            self.logger.warning(f"추출된 점수 {score}가 유효 범위(1-10)를 벗어남")
            score = None
      
      # 방법 2: '점수:' 형식 찾기 (이전 프롬프트와의 호환성)
      if score is None:
        score_lines = [line for line in review_result.split('\n') if
                       '점수:' in line and not ('종합' in line)]
        if score_lines:
          score_text = score_lines[0].split('점수:')[1].strip()
          # 숫자만 추출
          score_match = re.search(r'(\d+(\.\d+)?)', score_text)
          if score_match:
            score = float(score_match.group(1))
            self.logger.info(f"방법 2로 점수 추출 성공: {score} (원본 텍스트: '{score_text}')")
            
            # 점수가 1-10 범위를 벗어나면 무효화
            if score < 1 or score > 10:
              self.logger.warning(f"추출된 점수 {score}가 유효 범위(1-10)를 벗어남")
              score = None
      
      # 방법 3: 개별 평가 항목 점수 추출 및 평균 계산
      if score is None:
        # 정확성, 완전성, 논리성, 가독성, 통찰력 등의 항목별 점수 추출
        item_scores = []
        
        # 항목별 점수 패턴 (예: "1. 정확성: 8" 또는 "정확성: 8/10")
        patterns = [
          r'(\d+)\.\s*정확성:\s*(\d+(\.\d+)?)',  # 1. 정확성: 8
          r'정확성:\s*(\d+(\.\d+)?)',  # 정확성: 8
          r'완전성:\s*(\d+(\.\d+)?)',  # 완전성: 8
          r'논리성:\s*(\d+(\.\d+)?)',  # 논리성: 8
          r'가독성:\s*(\d+(\.\d+)?)',  # 가독성: 8
          r'통찰력:\s*(\d+(\.\d+)?)'  # 통찰력: 8
        ]
        
        for pattern in patterns:
          matches = re.findall(pattern, review_result)
          for match in matches:
            if isinstance(match, tuple):
              # 패턴에 따라 그룹 인덱스가 다를 수 있음
              score_str = match[0] if pattern.startswith(r'(\d+)\.') else match[0]
              try:
                item_score = float(score_str)
                if 1 <= item_score <= 10:  # 유효한 점수 범위 확인
                  item_scores.append(item_score)
              except ValueError:
                pass
        
        # 항목 점수가 3개 이상 있으면 평균 계산
        if len(item_scores) >= 3:
          score = sum(item_scores) / len(item_scores)
          self.logger.info(f"방법 3으로 점수 추출 성공: {score} (항목별 점수: {item_scores})")
      
      # 여전히 점수를 추출하지 못한 경우 기본값 설정
      if score is None:
        self.logger.warning(f"섹션 '{section['name']}'의 점수를 추출하지 못했습니다. 기본값 5.0 사용")
        score = 5.0  # 중간 점수로 기본 설정
      
      # 결과 저장
      review_info = {
        "section_index": i,
        "section_name": section["name"],
        "review": review_result,
        "score": score
      }
      review_results.append(review_info)
      
      # 점수가 낮은 섹션은 재생성 목록에 추가
      if score < 7.0:  # 7점 미만은 재생성 대상
        sections_to_regenerate.append(i)
        self.logger.info(f"섹션 '{section['name']}'의 점수가 {score}로 낮아 재생성 목록에 추가")
    
    # 노드 결과 로깅
    company_name = company_data.get("corp_name", "")
    if company_name:
      # 로그 내용 구성
      log_content = "## 보고서 검증 결과\n\n"
      for review in review_results:
        log_content += f"### {review['section_name']} (점수: {review['score']})\n\n"
        log_content += f"{review['review']}\n\n"
        if review['section_index'] in sections_to_regenerate:
          log_content += f"**재생성 필요** - 점수가 7.0 미만입니다.\n\n"
        log_content += "---\n\n"
      
      # 노드 결과를 메모리에 저장
      log_node_to_memory("review_report", log_content, "report_agent", company_name)
    
    # 상태 업데이트
    state["review_results"] = review_results
    
    # 재생성이 필요한 섹션이 있는 경우
    if sections_to_regenerate:
      self.logger.info(f"재생성이 필요한 섹션: {[sections[i]['name'] for i in sections_to_regenerate]}")
      state["sections_to_regenerate"] = sections_to_regenerate
      state["regeneration_mode"] = True
      state["current_section_index"] = sections_to_regenerate[0]
      state["next"] = "analyze_section"
    else:
      self.logger.info("모든 섹션이 품질 기준을 통과했습니다.")
      state["next"] = "compile_report"
    
    return state
  
  async def _compile_report(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """최종 보고서를 컴파일합니다."""
    self.logger.info("현재 노드: compile_report")
    sections = state["sections"]
    summary_card = state["summary_card"]
    company_data = state["company_data"]
    
    # 상세 보고서 컴파일
    detailed_content = []
    
    for section in sections:
      detailed_content.append(f"## {section['name']}\n\n{section['content']}")
    
    detailed_report = "\n\n".join(detailed_content)
    
    # 노드 결과 로깅
    company_name = company_data.get("corp_name", "")
    if company_name:
      # 로그 내용 구성
      log_content = "## 최종 보고서 컴파일 결과\n\n"
      log_content += "### 요약 카드\n\n"
      log_content += summary_card
      log_content += "\n\n### 상세 보고서\n\n"
      log_content += detailed_report
      
      # 노드 결과를 메모리에 저장
      log_node_to_memory("compile_report", log_content, "report_agent", company_name)
      
      # 최종 보고서 내용을 별도로 노드 로그에 추가
      log_node_to_memory("final_report", detailed_report, "report_agent", company_name)
    
    # 상태 업데이트
    state["detailed_report"] = detailed_report
    
    return state
  
  def _should_continue_analysis(self, state: Dict[str, Any]) -> bool:
    """모든 섹션 분석이 완료되었는지 확인합니다."""
    return state.get("all_analysis_done", False)
  
  async def _plan_sections(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """보고서 섹션을 계획합니다."""
    self.logger.info("현재 노드: plan_sections")
    company_data = state["company_data"]
    
    # 기본 섹션 구조
    sections = [{
      "name": "기업 개요",
      "description": "업력, 계열 구조, 산업 내 위치 등",
      "requires_calculation": False,
      "requires_research": True,
      "char_limit": 300,
      "content": ""
    }, {
      "name": "신용등급 평가 결과",
      "description": "신용등급 현황 정리",
      "requires_calculation": False,
      "requires_research": False,
      "char_limit": 200,
      "content": ""
    }, {
      "name": "재무상태 분석",
      "description": "손익계산서, 재무상태표, 현금흐름표 분석",
      "requires_calculation": True,
      "requires_research": False,
      "char_limit": 600,
      "content": ""
    }, {
      "name": "수익성 및 효율성 분석",
      "description": "ROE, ROA, 자산회전율 등 분석",
      "requires_calculation": True,
      "requires_research": False,
      "char_limit": 400,
      "content": ""
    }, {
      "name": "재무안정성 분석",
      "description": "부채비율, 이자보상배수 등 분석",
      "requires_calculation": True,
      "requires_research": False,
      "char_limit": 400,
      "content": ""
    }, {
      "name": "산업 및 경쟁사 비교",
      "description": "동종업계 내 위치 및 경쟁력",
      "requires_calculation": False,
      "requires_research": True,
      "char_limit": 500,
      "content": ""
    }, {
      "name": "유동성 분석",
      "description": "현금흐름, 운전자본, 유동성 위험 등 분석",  # 수정된 설명
      "requires_calculation": True,
      "requires_research": False,
      "char_limit": 400,
      "content": ""
    }, {
      "name": "리스크 요인 및 전망",
      "description": "주요 리스크와 향후 전망",
      "requires_calculation": True,
      "requires_research": True,
      "char_limit": 400,
      "content": ""
    }]
    
    # 상태 업데이트
    state["sections"] = sections
    state["current_section_index"] = 0
    state["all_analysis_done"] = False
    
    # 노드 결과 로깅
    company_name = company_data.get("corp_name", "")
    if company_name:
      # 로그 내용 구성
      log_content = "## 보고서 섹션 계획\n\n"
      for i, section in enumerate(sections):
        log_content += f"{i + 1}. **{section['name']}** ({section['description']})\n"
        log_content += f"   - 글자 수 제한: {section['char_limit']}자\n"
        log_content += f"   - 계산 필요: {'예' if section['requires_calculation'] else '아니오'}\n"
        log_content += f"   - 연구 필요: {'예' if section['requires_research'] else '아니오'}\n\n"
      
      # 노드 결과를 메모리에 저장
      log_node_to_memory("plan_sections", log_content, "report_agent", company_name)
    
    return state
  
  def _build_workflow(self) -> StateGraph:
    """워크플로우를 구성합니다."""
    workflow = StateGraph(ReportState)
    
    # 노드 추가
    workflow.add_node("plan_sections", self._plan_sections)
    workflow.add_node("calculate_ratios", self._calculate_additional_ratios)
    workflow.add_node("generate_summary", self._generate_summary_card)
    workflow.add_node("analyze_section", self._analyze_section)
    workflow.add_node("review_report", self._review_report)
    workflow.add_node("compile_report", self._compile_report)
    
    # 엣지 추가
    workflow.add_edge(START, "plan_sections")
    workflow.add_edge("plan_sections", "calculate_ratios")
    workflow.add_edge("calculate_ratios", "generate_summary")
    workflow.add_edge("generate_summary", "analyze_section")
    
    # 조건부 엣지 추가
    workflow.add_conditional_edges(
      "analyze_section",
      self._should_continue_analysis,
      {
        True: "review_report",  # 분석이 끝났으면 review_report로
        False: "analyze_section"  # 분석을 계속해야 하면 다시 analyze_section으로
      })
    
    # review_report에서 다음 노드 결정을 위한 조건부 엣지 추가
    def _get_next_node(state: ReportState) -> str:
      return state.next or "compile_report"  # next 값이 없으면 기본적으로 compile_report로
    
    workflow.add_conditional_edges("review_report", _get_next_node, {
      "analyze_section": "analyze_section",
      "compile_report": "compile_report"
    })
    
    workflow.add_edge("compile_report", END)
    
    return workflow
  
  async def generate_report(self, company_name: str, credit_rating_result: Dict[str, Any],
      financial_data: Dict[str, Any]) -> Dict[str, Any]:
    """
        보고서를 생성합니다.
        
        Args:
            company_name: 기업명
            credit_rating_result: 신용등급 평가 결과
            financial_data: 재무제표 데이터
            
        Returns:
            Dict[str, Any]: 생성된 보고서
        """
    # 로깅 시작
    self.logger.info(f"'{company_name}' 기업 보고서 생성 시작")
    start_time = time.time()
    
    # 단위 정보 로깅을 위해 추출
    unit = financial_data.get('unit', '원')
    
    # 초기 상태 생성
    initial_state = self._initialize_state(company_name, credit_rating_result, financial_data)
    
    # 워크플로우 생성
    workflow = self._build_workflow()
    
    # 그래프 컴파일
    graph = workflow.compile()
    
    # 체크포인트 설정
    config = {"checkpointer": MemorySaver()}
    
    # 실행
    try:
      # Pydantic v1과 v2 모두 호환되도록 수정
      # dict() 메서드가 있으면 사용하고, 없으면 model_dump() 사용
      if hasattr(initial_state, "model_dump"):
        state_dict = initial_state.model_dump()
      else:
        # 둘 다 없는 경우 직접 변환
        state_dict = {k: v for k, v in initial_state.__dict__.items() if not k.startswith('_')}
      
      final_state = await graph.ainvoke(state_dict, config)
      
      # 최종 보고서 생성 결과
      result = {
        "company_name": company_name,
        "summary_card": final_state["summary_card"],
        "summary_card_structured": final_state.get("summary_card_structured", {}),
        # 구조화된 요약 카드 데이터 추가
        "detailed_report": final_state["detailed_report"],
        "sections": final_state["sections"],
        "credit_rating": final_state["credit_rating"],  # 신용등급 정보 추가
        "generated_at": datetime.now().isoformat()
      }
      
      # 모든 노드 로그를 하나의 파일로 저장
      from app.utils.logging_utils import save_node_logs_to_file
      save_node_logs_to_file('report_agent', company_name, unit)
      
      # 메모리에 저장된 다른 로그는 저장하지 않음
      # save_logs_to_files('report_agent', company_name)
      
      # 로깅 완료
      end_time = time.time()
      self.logger.info(f"'{company_name}' 기업 보고서 생성 완료 (소요 시간: {end_time - start_time:.2f}초)")
      
      return result
    except Exception as e:
      self.logger.error(f"보고서 생성 중 오류 발생: {str(e)}")
      traceback.print_exc()
      raise
