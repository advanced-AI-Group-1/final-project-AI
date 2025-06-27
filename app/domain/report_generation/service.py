from datetime import datetime
from typing import Dict, Any, Optional, List

from app.domain.report_generation.agent import ReportAgent
from app.domain.report_generation.templates import format_report_data
from app.infrastructure.llm.manager import LLMManager


class ReportGenerationService:
  """
  신용평가 결과와 재무제표 데이터를 기반으로 보고서를 생성하는 서비스 클래스
  """

  def __init__(self):
    self.llm_manager = LLMManager()
    self.report_agent = ReportAgent()

  async def generate_report(self,
      company_name: str,
      credit_rating_result: Dict[str, Any],
      financial_data: Dict[str, Any],
      report_type: str = "agent_based",
      additional_context: Optional[str] = None) -> Dict[str, Any]:
    """
    AI 에이전트를 통해 보고서를 생성합니다.

    Args:
        company_name (str): 기업명
        credit_rating_result (Dict[str, Any]): 신용평가 결과
        financial_data (Dict[str, Any]): 재무제표 데이터
        report_type (str): 보고서 유형 (standard, detailed, executive_summary 등)
        additional_context (Optional[str]): 추가 컨텍스트 정보

    Returns:
        Dict[str, Any]: 생성된 보고서
    """
    # 보고서 유형에 따라 다른 생성 방식 사용
    if report_type == "agent_based":
      return await self.generate_agent_based_report(company_name,
                                                    credit_rating_result,
                                                    financial_data)

    # 기존 방식으로 보고서 생성
    # 보고서 생성을 위한 프롬프트 구성
    prompt = self._construct_report_prompt(company_name, credit_rating_result,
                                           financial_data, report_type,
                                           additional_context)

    # LLM을 통한 보고서 생성
    report_content = await self.llm_manager.generate_response(prompt)

    # 보고서 섹션 분리 및 구조화
    report_sections = self._parse_report_sections(report_content)

    # 현재 시간을 ISO 형식으로 변환
    generated_at = datetime.now().isoformat()

    # 보고서 데이터 포맷팅
    report_data = format_report_data(
        company_name=company_name,
        summary_card="",  # 요약 카드 없음
        detailed_report=report_content,
        generated_at=generated_at
    )

    # 섹션 형식 변환
    formatted_sections = [
      {"title": section["title"], "content": section["content"]} for section in
      report_sections]

    return {
      "company_name": company_name,
      "report_data": report_data,
      "sections": formatted_sections,
      "credit_rating": credit_rating_result,
      "generated_at": generated_at,
      "report_type": report_type
    }

  async def generate_agent_based_report(self, company_name: str,
      credit_rating_result: Dict[str, Any],
      financial_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph 기반 에이전트를 사용하여 보고서를 생성합니다.

    Args:
        company_name (str): 기업명
        credit_rating_result (Dict[str, Any]): 신용평가 결과
        financial_data (Dict[str, Any]): 재무제표 데이터

    Returns:
        Dict[str, Any]: 생성된 보고서
    """
    # 에이전트를 통한 보고서 생성
    report_result = await self.report_agent.generate_report(company_name,
                                                            credit_rating_result,
                                                            financial_data)

    # 보고서 데이터 포맷팅
    report_data = format_report_data(
        company_name=company_name,
        summary_card=report_result["summary_card"],
        detailed_report=report_result["detailed_report"],
        generated_at=report_result["generated_at"]
    )

    # 에이전트가 반환한 섹션을 API 응답 형식으로 변환
    formatted_sections = []
    for section in report_result["sections"]:
      # 필요한 정보만 포함하여 변환 (name -> title, description과 content는 그대로 유지)
      formatted_sections.append({
        "title": section["name"],
        "description": section["description"],
        "content": section["content"]
      })

    return {
      "company_name": company_name,
      "report_data": report_data,
      "sections": formatted_sections,
      "credit_rating": credit_rating_result,
      "generated_at": report_result["generated_at"],
      "report_type": "agent_based",
      "summary_card_structured": report_result.get("summary_card_structured",
                                                   {})  # 구조화된 요약 카드 데이터 추가
    }

  def _construct_report_prompt(self, company_name: str,
      credit_rating_result: Dict[str, Any], financial_data: Dict[str,
      Any],
      report_type: str, additional_context: Optional[str]) -> str:
    """
    보고서 생성을 위한 LLM 프롬프트를 구성합니다.
    """
    # 보고서 유형에 따른 지시사항 설정
    report_instructions = {
      "standard": "표준 형식의 신용평가 보고서를 작성해주세요. 주요 재무지표 분석과 신용등급 산출 근거를 포함해야 합니다.",
      "detailed": "상세한 신용평가 보고서를 작성해주세요. 모든 재무지표에 대한 심층 분석과 업계 비교, 미래 전망을 포함해야 합니다.",
      "executive_summary": "경영진을 위한 요약 보고서를 작성해주세요. 핵심 정보만 간결하게 제시하고 주요 의사결정 포인트를 강조해야 합니다."
    }

    instruction = report_instructions.get(report_type,
                                          report_instructions["standard"])

    prompt = f"""
        당신은 금융 보고서 작성 전문가입니다. {company_name} 기업에 대한 신용평가 보고서를 작성해주세요.
        
        {instruction}
        
        ## 기업 정보
        기업명: {company_name}
        
        ## 신용평가 결과
        {credit_rating_result}
        
        ## 재무제표 데이터
        {financial_data}
        
        ## 보고서 형식
        보고서는 다음 섹션으로 구성해주세요:
        
        1. 요약 (Executive Summary)
        2. 기업 개요 (Company Overview)
        3. 재무 분석 (Financial Analysis)
          - 수익성 (Profitability)
          - 안정성 (Stability)
          - 성장성 (Growth)
          - 현금흐름 (Cash Flow)
        4. 신용등급 평가 (Credit Rating Assessment)
        5. 위험 요소 (Risk Factors)
        6. 결론 및 제언 (Conclusion and Recommendations)
        
        각 섹션은 명확하게 구분되어야 하며, 섹션 제목을 포함해주세요.
        """

    if additional_context:
      prompt += f"\n## 추가 정보\n{additional_context}\n"

    return prompt

  def _parse_report_sections(self, report_content: str) -> List[Dict[str, Any]]:
    """
    보고서 내용을 섹션별로 분리하여 구조화합니다.
    """
    # 섹션 제목 패턴 (예: "1. 요약", "## 재무 분석" 등)
    import re

    # 섹션 구분을 위한 정규식 패턴
    section_patterns = [
      r"#+\s*(.*?)\s*\n",  # Markdown 형식 (## 제목)
      r"\d+\.\s*(.*?)\s*\n"  # 번호 형식 (1. 제목)
    ]

    sections = []
    current_section = {"title": "서문", "content": ""}

    lines = report_content.split("\n")
    for line in lines:
      is_new_section = False

      # 섹션 제목 확인
      for pattern in section_patterns:
        match = re.match(pattern, line)
        if match:
          # 이전 섹션 저장
          if current_section["content"].strip():
            sections.append(current_section)

          # 새 섹션 시작
          current_section = {"title": match.group(1), "content": line + "\n"}
          is_new_section = True
          break

      if not is_new_section:
        current_section["content"] += line + "\n"

    # 마지막 섹션 추가
    if current_section["content"].strip():
      sections.append(current_section)

    return sections
