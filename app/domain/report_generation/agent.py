"""
LangGraph를 사용한 보고서 생성 에이전트 구현
"""
from datetime import datetime
from typing import Dict, Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END

from app.domain.report_generation.models import ReportState, AdditionalRatioCalculator
from app.domain.report_generation.prompts import (SUMMARY_CARD_PROMPT, FINANCIAL_ANALYSIS_PROMPT,
                                                  CREDIT_RATING_ANALYSIS_PROMPT, CONCLUSION_PROMPT,
                                                  DEFAULT_SECTIONS)
from app.infrastructure.llm.manager import LLMManager


class ReportAgent:
  """
    LangGraph를 사용한 보고서 생성 에이전트
    """
  
  def __init__(self):
    self.llm_manager = LLMManager()
  
  async def _call_llm(self, prompt: str) -> str:
    """LLM을 호출하여 응답을 생성합니다."""
    return await self.llm_manager.generate_response(prompt)
  
  def _format_financial_data(self, financial_data: Dict[str, Any]) -> str:
    """재무 데이터를 문자열로 포맷팅합니다."""
    result = []
    
    # 기본 정보
    result.append(f"기업명: {financial_data.get('corp_name', '')}")
    result.append(f"업종: {financial_data.get('industry_name', '')}")
    result.append(f"시장구분: {financial_data.get('market_type', '')}")
    
    # 손익계산서
    result.append("\n[손익계산서]")
    result.append(f"매출액: {financial_data.get('revenue', 0):,.0f}원")
    result.append(
      f"영업이익: {financial_data.get('operating_profit', 0):,.0f}원 (이익률: {financial_data.get('operating_profit', 0) / financial_data.get('revenue', 1) * 100:.2f}%)"
    )
    result.append(
      f"당기순이익: {financial_data.get('net_income', 0):,.0f}원 (이익률: {financial_data.get('net_income', 0) / financial_data.get('revenue', 1) * 100:.2f}%)"
    )
    
    # 재무상태표
    result.append("\n[재무상태표]")
    result.append(f"총자산: {financial_data.get('total_assets', 0):,.0f}원")
    result.append(f"총부채: {financial_data.get('total_liabilities', 0):,.0f}원")
    result.append(f"자본총계: {financial_data.get('total_equity', 0):,.0f}원")
    
    # 주요 재무비율
    result.append("\n[주요 재무비율]")
    result.append(f"부채비율: {financial_data.get('debt_ratio', 0) * 100:.2f}%")
    result.append(f"ROA(총자산이익률): {financial_data.get('ROA', 0) * 100:.2f}%")
    result.append(f"ROE(자기자본이익률): {financial_data.get('ROE', 0) * 100:.2f}%")
    result.append(f"매출총자산회전율: {financial_data.get('asset_turnover_ratio', 0):.2f}회")
    
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
    # DEFAULT_SECTIONS의 각 섹션에 content 키를 추가
    sections_with_content = []
    for section in DEFAULT_SECTIONS:
        section_copy = section.copy()
        section_copy["content"] = ""  # 빈 content 필드 추가
        sections_with_content.append(section_copy)
        
    return ReportState(company_data=financial_data,
                       credit_rating=credit_rating_result,
                       sections=sections_with_content,
                       current_section_index=0,
                       all_analysis_done=False)
  
  async def _calculate_additional_ratios(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """추가 재무비율을 계산합니다."""
    company_data = state["company_data"]
    
    # 추가 재무비율 계산
    additional_ratios = AdditionalRatioCalculator.calculate_all_additional_ratios(company_data)
    
    # 상태 업데이트
    state["additional_ratios"] = additional_ratios
    
    return state
  
  async def _generate_summary_card(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """요약 카드를 생성합니다."""
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
    summary_card = await self._call_llm(prompt)
    
    # 상태 업데이트
    state["summary_card"] = summary_card
    
    return state
  
  async def _analyze_section(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """현재 섹션을 분석합니다."""
    company_data = state["company_data"]
    credit_rating = state["credit_rating"]
    sections = state["sections"]
    current_index = state["current_section_index"]
    additional_ratios = state.get("additional_ratios", {})
    
    if current_index >= len(sections):
      state["all_analysis_done"] = True
      # LangGraph 버전 호환성을 위해 다음 노드를 명시적으로 지정
      state["next"] = "compile_report"
      return state
    
    current_section = sections[current_index]
    
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
            
            다음 재무 데이터와 신용등급 정보를 바탕으로 '{current_section['name']}' 섹션을 작성해주세요:
            
            재무 데이터:
            {self._format_financial_data(company_data)}
            
            신용등급 정보:
            {self._format_credit_rating(credit_rating)}
            
            섹션 설명: {current_section['description']}
            글자 수 제한: {current_section['char_limit']}자 이내
            """
    
    # LLM 호출
    section_content = await self._call_llm(prompt)
    
    # 섹션 내용 업데이트
    sections[current_index]["content"] = section_content
    
    # 다음 섹션으로 이동
    state["current_section_index"] = current_index + 1
    
    # LangGraph 버전 호환성을 위해 다음 노드를 명시적으로 지정
    # 모든 섹션이 완료되었는지 확인하여 다음 노드 결정
    if state["current_section_index"] >= len(sections):
      state["all_analysis_done"] = True
      state["next"] = "compile_report"
    else:
      state["next"] = "analyze_section"
    
    return state
  
  async def _compile_report(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """최종 보고서를 컴파일합니다."""
    sections = state["sections"]
    summary_card = state["summary_card"]
    
    # 상세 보고서 컴파일
    detailed_content = []
    
    for section in sections:
      detailed_content.append(f"## {section['name']}\n\n{section['content']}")
    
    detailed_report = "\n\n".join(detailed_content)
    
    # 상태 업데이트
    state["detailed_report"] = detailed_report
    
    return state
  
  def _should_continue_analysis(self, state: Dict[str, Any]) -> bool:
    """분석을 계속해야 하는지 확인합니다."""
    return not state["all_analysis_done"]
  
  def _create_workflow(self):
    """워크플로우를 생성하고 반환합니다."""
    # 워크플로우 정의
    workflow = StateGraph(ReportState)
    
    # 노드 추가
    workflow.add_node("calculate_ratios", self._calculate_additional_ratios)
    workflow.add_node("generate_summary", self._generate_summary_card)
    workflow.add_node("analyze_section", self._analyze_section)
    workflow.add_node("compile_report", self._compile_report)
    
    # 엣지 추가
    workflow.add_edge(START, "calculate_ratios")
    workflow.add_edge("calculate_ratios", "generate_summary")
    workflow.add_edge("generate_summary", "analyze_section")
    
    # 조건부 엣지 추가
    workflow.add_conditional_edges(
        "analyze_section",
        self._should_continue_analysis,
        {
            True: "analyze_section",  # 분석을 계속해야 하면 다시 analyze_section으로
            False: "compile_report"   # 분석이 끝났으면 compile_report로
        }
    )
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
    # 초기 상태 생성
    initial_state = self._initialize_state(company_name, credit_rating_result, financial_data)
    
    # 워크플로우 생성
    workflow = self._create_workflow()
    
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
      
      return {
        "company_name": company_name,
        "summary_card": final_state["summary_card"],
        "detailed_report": final_state["detailed_report"],
        "sections": final_state["sections"],
        "generated_at": datetime.now().isoformat()
      }
    except Exception as e:
      print(f"보고서 생성 중 오류 발생: {str(e)}")
      raise e
