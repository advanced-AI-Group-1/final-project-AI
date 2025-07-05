import json
import logging
import re
from typing import TypedDict, Dict, Any, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

# 로거 설정
logger = logging.getLogger(__name__)


# 상태 정의
class AgentState(TypedDict):
  financial_data: Dict[str, Any]
  current_rating: str
  validation_issues: List[str]
  needs_agent_validation: bool
  final_rating: str
  final_reason: str
  is_adjusted: bool


class AgentValidator:
  """신용등급 검증을 위한 LangGraph 에이전트"""
  
  def __init__(self, openai_api_key: str):
    self.llm = ChatOpenAI(
      model="gpt-4-turbo-preview",
      temperature=0.2,
      api_key=openai_api_key
    )
    self.parser = JsonOutputParser()
    self.agent = self._build_agent()
  
  def _build_agent(self):
    """LangGraph 에이전트 빌드"""
    # 에이전트 워크플로우 정의
    workflow = StateGraph(AgentState)
    
    # 노드 추가
    workflow.add_node("evaluate_rating", self._evaluate_rating)
    workflow.add_node("skip_validation", self._skip_validation)
    
    # 엣지 추가
    workflow.add_conditional_edges(
      "evaluate_rating",
      self._should_skip_validation,
      {
        "validate": END,
        "skip": "skip_validation"
      }
    )
    workflow.add_edge("skip_validation", END)
    
    # 초기 엔트리 포인트 설정
    workflow.set_entry_point("evaluate_rating")
    
    return workflow.compile()
  
  def _should_skip_validation(self, state: AgentState) -> str:
    """에이전트 검증을 건너뛸지 결정"""
    # 이미 룰 기반에서 확정된 경우 검증 건너뜀
    if not state["needs_agent_validation"]:
      return "skip"
    
    data = state["financial_data"]
    
    # 🆕 AAA 등급 우대 조건 추가 (완화된 기준)
    if state["current_rating"] == "AAA":
      debt_ratio = data.get('debt_ratio', 0)
      current_ratio = data.get('current_ratio', 0)
      operating_margin = data.get('operating_profit_margin', 0)
      
      # AAA 우대 조건 (더 관대한 기준)
      if (debt_ratio < 0.4 and  # 부채비율 40% 미만
          current_ratio > 1.0 and  # 유동비율 1.0 초과
          operating_margin > 0.06):  # 영업이익률 6% 초과
        logger.info(f"AAA 등급 우대 조건 만족 - 에이전트 검증 건너뛰기")
        return "skip"
    
    # 명확한 케이스: 에이전트 검증 건너뛰기
    if (data.get("total_equity", 0) <= 0 or  # 완전 자본잠식
        data.get("total_liabilities", 0) > data.get("total_assets", 1) or  # 부채 > 자산
        state["current_rating"] in ["D", "E"] or  # 이미 최하위 등급
        (data.get("operating_cash_flow", 0) < 0 and  # 영업현금흐름이 마이너스이며
         abs(data.get("operating_cash_flow", 0)) > data.get("interest_expense", 1))):  # 이자지급 능력 없음
      return "skip"
    
    return "validate"
  
  def _evaluate_rating(self, state: AgentState) -> Dict[str, Any]:
    """LLM을 사용해 신용등급 검증 및 조정"""
    prompt = self._create_evaluation_prompt(state)
    
    try:
      # LLM 호출
      response = self.llm.invoke([
        SystemMessage(
          content="당신은 금융 전문가입니다. 주어진 재무 데이터와 검증 이슈를 바탕으로 신용등급의 적절성을 분석하고, 필요시 조정된 등급을 제안하세요."),
        HumanMessage(content=prompt)
      ])
      
      # 응답 파싱
      result = self._parse_llm_response(response.content, state["current_rating"])
      return result
    
    except Exception as e:
      logger.error(f"에이전트 평가 중 오류: {str(e)}")
      return {
        "final_rating": state["current_rating"],
        "final_reason": f"에이전트 평가 중 오류: {str(e)}",
        "is_adjusted": False
      }
  
  def _create_evaluation_prompt(self, state: AgentState) -> str:
    """평가를 위한 프롬프트 생성 (AAA 등급 기준 명확화)"""
    data = state["financial_data"]
    
    prompt = f"""
        다음은 기업의 재무 데이터와 현재 부여된 신용등급, 그리고 검증 과정에서 발견된 이슈들입니다.
        이 정보를 바탕으로 신용등급이 적절한지 분석하고, 필요시 조정된 등급을 제안해주세요.

        [기본 정보]
        - 기업명: {data.get('company_name', '알 수 없음')}
        - 산업: {data.get('industry_name', '알 수 없음')}

        [재무 데이터]
        - 자산: {data.get('total_assets', 0):,}원
        - 부채: {data.get('total_liabilities', 0):,}원
        - 자본: {data.get('total_equity', 0):,}원
        - 매출액: {data.get('revenue', 0):,}원
        - 영업이익: {data.get('operating_profit', 0):,}원
        - 당기순이익: {data.get('net_income', 0):,}원
        - 영업현금흐름: {data.get('operating_cash_flow', 0):,}원
        - 부채비율: {data.get('debt_ratio', 0) * 100:.1f}%
        - 유동비율: {data.get('current_ratio', 0):.2f}
        - 영업이익률: {data.get('operating_profit_margin', 0) * 100:.1f}%
        - ROA: {data.get('ROA', 0) * 100:.1f}%
        - ROE: {data.get('ROE', 0) * 100:.1f}%

        [현재 신용등급]: {state["current_rating"]}
        [검증 이슈]:
        """
    
    # 검증 이슈 추가
    if state["validation_issues"]:
      for issue in state["validation_issues"]:
        prompt += f"- {issue}\n"
    else:
      prompt += "- 없음\n"
    
    # 긍정적/부정적 요인 추가
    if data.get("positive_factors"):
      prompt += "\n[긍정적 요인]:\n"
      if isinstance(data["positive_factors"], list):
        for factor in data["positive_factors"]:
          prompt += f"- {factor}\n"
      else:
        prompt += f"- {data['positive_factors']}\n"
    
    if data.get("negative_factors"):
      prompt += "\n[부정적 요인]:\n"
      if isinstance(data["negative_factors"], list):
        for factor in data["negative_factors"]:
          prompt += f"- {factor}\n"
      else:
        prompt += f"- {data['negative_factors']}\n"
    
    # 🆕 신용등급별 명확한 기준 제시
    prompt += """

        [신용등급 평가 기준]

        🏆 AAA 등급 (최우량):
        - 부채비율: 30% 이하 (0.3 이하)
        - ROA: 5% 이상 (0.05 이상)
        - 영업이익률: 8% 이상 (0.08 이상)
        - 유동비율: 1.2 이상
        - 안정적 현금흐름 (영업현금흐름 > 0)
        - 업계 최상위 기업 (삼성전자, LG화학, 현대자동차 등)

        🥇 AA 등급 (우량):
        - 부채비율: 50% 이하
        - ROA: 3% 이상
        - 영업이익률: 5% 이상
        - 현금흐름 양호

        🥈 A 등급 (양호):
        - 부채비율: 100% 이하
        - ROA: 1% 이상
        - 수익성 안정적

        ⚠️ 중요 지침:
        1. 위 AAA 기준을 모두 만족하는 기업은 AAA 등급을 강하게 고려하세요.
        2. 특히 대기업이면서 재무지표가 우수한 경우 보수적 조정을 피하세요.
        3. 산업 특성을 고려하되, 객관적 재무지표가 우수하면 높은 등급을 유지하세요.
        4. 단순한 업종 위험만으로는 등급을 하향하지 마세요.
        5. 삼성전자, LG화학, 현대자동차 같은 국내 최상위 기업은 AAA 유지를 우선 고려하세요.

        [분석 지시사항]
        1. 재무 건전성 종합 평가
        2. 수익성 및 성장성 분석
        3. 현금흐름 안정성 검토
        4. 업종별 비교 분석 (하지만 과도한 업종 위험 적용 금지)
        5. 검증 이슈의 실질적 영향도 평가
        6. 최종 등급 결정 및 상세 근거 제시

        [응답 형식]
        {{
            "final_rating": "최종 신용등급",
            "is_adjusted": true/false,
            "reason": "상세한 분석과 조정 사유"
        }}
        """
    
    return prompt
  
  def _parse_llm_response(self, response: str, current_rating: str) -> Dict[str, Any]:
    """LLM 응답 파싱"""
    try:
      # JSON 형식으로 파싱 시도
      try:
        result = json.loads(response.strip())
        if not all(key in result for key in ["final_rating", "is_adjusted", "reason"]):
          raise ValueError("필수 키가 없습니다.")
        return result
      except (json.JSONDecodeError, ValueError):
        # JSON 파싱 실패 시 추출 시도
        final_rating = current_rating
        is_adjusted = False
        reason = "응답 파싱 오류로 인해 원래 등급 유지"
        
        # 등급 추출 시도
        if "final_rating" in response:
          rating_match = re.search(r'"final_rating"\s*:\s*"([A-Za-z0-9+-]+)"', response)
          if rating_match:
            final_rating = rating_match.group(1)
            is_adjusted = final_rating != current_rating
        
        # 사유 추출 시도
        if "reason" in response:
          reason_match = re.search(r'"reason"\s*:\s*"([^"]+)"', response)
          if reason_match:
            reason = reason_match.group(1)
        
        return {
          "final_rating": final_rating,
          "is_adjusted": is_adjusted,
          "reason": reason
        }
    
    except Exception as e:
      logger.error(f"응답 파싱 중 오류: {str(e)}")
      return {
        "final_rating": current_rating,
        "is_adjusted": False,
        "reason": f"응답 파싱 오류: {str(e)}"
      }
  
  def _skip_validation(self, state: AgentState) -> Dict[str, Any]:
    """검증 건너뛰기"""
    return {
      "final_rating": state["current_rating"],
      "final_reason": "명확한 케이스로 인해 검증이 건너뛰어졌습니다.",
      "is_adjusted": False
    }
  
  async def validate_rating(
      self,
      financial_data: Dict[str, Any],
      initial_rating: str,
      validation_issues: List[str] = None
  ) -> Dict[str, Any]:
    """신용등급 검증 실행"""
    if validation_issues is None:
      validation_issues = []
    
    # 초기 상태 설정
    state = {
      "financial_data": financial_data,
      "current_rating": initial_rating,
      "validation_issues": validation_issues,
      "needs_agent_validation": True,
      "final_rating": initial_rating,
      "final_reason": "",
      "is_adjusted": False
    }
    
    # 에이전트 실행
    try:
      result = await self.agent.ainvoke(state)
      return result
    except Exception as e:
      logger.error(f"에이전트 실행 중 오류: {str(e)}")
      return {
        "final_rating": initial_rating,
        "is_adjusted": False,
        "reason": f"에이전트 실행 오류: {str(e)}"
      }


# 에이전트 인스턴스 캐시
_agent_instance = None


def get_credit_rating_agent(openai_api_key: str) -> "AgentValidator":
  """에이전트 인스턴스 싱글톤 반환"""
  global _agent_instance
  if _agent_instance is None:
    _agent_instance = AgentValidator(openai_api_key)
  return _agent_instance
