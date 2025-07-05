import asyncio
import json
import logging
import os
import re
from typing import Dict, Any, Optional, List

from dotenv import load_dotenv

from app.domain.credit_rating.validation import comprehensive_credit_validation
from app.infrastructure.llm.runpod_manager import RunPodLLMManager
from app.infrastructure.search.tavily_search import TavilySearchService
from app.utils.financial_utils import normalize_unit
from app.utils.logging_utils import log_to_file
from .agent_validator import get_credit_rating_agent


# 에이전트 초기화
logger = logging.getLogger(__name__)

"""
    신용등급 평가 서비스
"""
load_dotenv()


class CreditRatingService:
  
  def __init__(self, openai_api_key: Optional[str] = None):
    self.llm_manager = RunPodLLMManager()
    self.tavily_search_service = TavilySearchService()
    self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
    self._agent = None
    self.credit_rating_agent = get_credit_rating_agent(self.openai_api_key)
  
  @property
  def agent(self):
    """에이전트 인스턴스를 반환합니다."""
    return self._agent
  
  def _calculate_estimated_current_ratio(self, financial_data: Dict[str, Any]) -> float:
    """
    유동비율 추정 계산

    Args:
        financial_data: 재무 데이터

    Returns:
        float: 추정 유동비율
    """
    try:
      # 업종별 추정 비율 적용
      industry = financial_data.get('industry_name', '')
      
      # 업종별 유동자산/총자산 비율 추정
      if '제조업' in industry or '전자' in industry or '반도체' in industry or '통신' in industry:
        current_asset_ratio = 0.55  # 제조업/전자업: 55%
        current_liability_ratio = 0.65  # 유동부채/총부채: 65%
      elif '서비스업' in industry or '소프트웨어' in industry:
        current_asset_ratio = 0.65  # 서비스업: 65%
        current_liability_ratio = 0.75  # 유동부채/총부채: 75%
      elif '건설업' in industry:
        current_asset_ratio = 0.70  # 건설업: 70%
        current_liability_ratio = 0.80  # 유동부채/총부채: 80%
      elif '금융' in industry or '은행' in industry:
        current_asset_ratio = 0.75  # 금융업: 75%
        current_liability_ratio = 0.85  # 유동부채/총부채: 85%
      else:
        current_asset_ratio = 0.60  # 기본값: 60%
        current_liability_ratio = 0.70  # 기본값: 70%
      
      # 추정 계산
      total_assets = financial_data.get('total_assets', 0)
      total_liabilities = financial_data.get('total_liabilities', 0)
      
      if total_assets > 0 and total_liabilities > 0:
        estimated_current_assets = total_assets * current_asset_ratio
        estimated_current_liabilities = total_liabilities * current_liability_ratio
        
        if estimated_current_liabilities > 0:
          estimated_ratio = estimated_current_assets / estimated_current_liabilities
          logger.info(f"추정 유동비율 계산: {estimated_ratio:.2f} (업종: {industry})")
          return estimated_ratio
      
      # 기본값 반환 (보수적 추정)
      return 1.2
    
    except Exception as e:
      logger.warning(f"유동비율 추정 계산 중 오류: {str(e)}")
      return 1.2
  
  def _calculate_derived_metrics(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    파생 지표 계산 (유동비율 추정 로직 추가)

    Args:
        financial_data (Dict[str, Any]): 재무 데이터

    Returns:
        Dict[str, Any]: 파생 지표가 추가된 재무 데이터
    """
    # 단위 표준화 (원 단위로 통일)
    data = normalize_unit(financial_data)
    
    # 부채비율 계산 (총부채 / 자본총계)
    if ('total_liabilities' in data and 'total_equity' in data and
        data['total_equity'] is not None and
        data['total_liabilities'] is not None):
      if 'debt_ratio' not in data or data['debt_ratio'] == 0:
        # 자본이 0이거나 음수인 경우 특별 처리
        if data['total_equity'] <= 0:
          # 자본잠식 상태이므로 매우 높은 부채비율로 설정 (999.99)
          data['debt_ratio'] = 999.99
          # 자본잠식 상태 표시를 위한 플래그 추가
          data['is_capital_impaired'] = True
        else:
          # 정상적인 부채비율 계산
          data['debt_ratio'] = data['total_liabilities'] / data['total_equity']
          data['is_capital_impaired'] = False
    
    # ROA 계산 (당기순이익 / 총자산)
    if ('net_income' in data and 'total_assets' in data and
        data['total_assets'] is not None and data['total_assets'] != 0 and
        data['net_income'] is not None):
      if 'ROA' not in data or data['ROA'] == 0:
        data['ROA'] = data['net_income'] / data['total_assets']
    
    # ROE 계산 (당기순이익 / 자본총계)
    if ('net_income' in data and 'total_equity' in data and
        data['total_equity'] is not None and data['total_equity'] != 0 and
        data['net_income'] is not None):
      if 'ROE' not in data or data['ROE'] == 0:
        data['ROE'] = data['net_income'] / data['total_equity']
    
    # 유동비율 추정 계산 로직 추가
    if 'current_ratio' not in data or data.get('current_ratio', 0) == 0:
      data['current_ratio'] = self._calculate_estimated_current_ratio(data)
    
    # 영업이익률 계산 로직 추가
    if 'operating_profit_margin' not in data or data.get('operating_profit_margin', 0) == 0:
      if data.get('operating_profit') and data.get('revenue') and data['revenue'] > 0:
        data['operating_profit_margin'] = data['operating_profit'] / data['revenue']
      else:
        data['operating_profit_margin'] = 0
    
    # 총자산회전율 계산 (매출액 / 총자산)
    if ('revenue' in data and 'total_assets' in data and
        data['total_assets'] is not None and data['total_assets'] != 0 and
        data['revenue'] is not None):
      if 'asset_turnover_ratio' not in data or data['asset_turnover_ratio'] == 0:
        data['asset_turnover_ratio'] = data['revenue'] / data['total_assets']
    
    # 이자총자산비율 계산 (이자발생부채 / 총자산)
    if ('interest_bearing_debt' in data and 'total_assets' in data and
        data['total_assets'] is not None and data['total_assets'] != 0 and
        data['interest_bearing_debt'] is not None):
      if 'interest_to_assets_ratio' not in data or data['interest_to_assets_ratio'] == 0:
        data['interest_to_assets_ratio'] = data['interest_bearing_debt'] / data['total_assets']
    
    # 이자매출비율 계산 (이자발생부채 / 매출액)
    if ('interest_bearing_debt' in data and 'revenue' in data and
        data['revenue'] is not None and data['revenue'] != 0 and
        data['interest_bearing_debt'] is not None):
      if 'interest_to_revenue_ratio' not in data or data['interest_to_revenue_ratio'] == 0:
        data['interest_to_revenue_ratio'] = data['interest_bearing_debt'] / data['revenue']
    
    # 현금흐름대비이자 계산 (영업활동현금흐름 / 이자발생부채)
    if ('operating_cash_flow' in data and 'interest_bearing_debt' in data and
        data['interest_bearing_debt'] is not None and data['interest_bearing_debt'] != 0 and
        data['operating_cash_flow'] is not None):
      if 'cash_flow_to_interest' not in data or data['cash_flow_to_interest'] is None:
        data['cash_flow_to_interest'] = data['operating_cash_flow'] / data['interest_bearing_debt']
    else:
      # 계산에 필요한 데이터가 없는 경우 기본값 설정
      if 'cash_flow_to_interest' not in data or data['cash_flow_to_interest'] is None:
        data['cash_flow_to_interest'] = 0.0
    
    # 이자대비현금흐름 계산 (이자발생부채 / 영업활동현금흐름)
    if ('interest_bearing_debt' in data and 'operating_cash_flow' in data and
        data['operating_cash_flow'] is not None and data['operating_cash_flow'] != 0 and
        data['interest_bearing_debt'] is not None):
      if 'interest_to_cash_flow' not in data or data['interest_to_cash_flow'] is None:
        data['interest_to_cash_flow'] = data['interest_bearing_debt'] / data['operating_cash_flow']
    else:
      # 계산에 필요한 데이터가 없는 경우 기본값 설정
      if 'interest_to_cash_flow' not in data or data['interest_to_cash_flow'] is None:
        data['interest_to_cash_flow'] = 0.0
    
    # 로그 총자산 계산
    if 'total_assets' in data and data['total_assets'] is not None and data['total_assets'] > 0:
      import math
      if 'log_total_assets' not in data or data['log_total_assets'] == 0:
        data['log_total_assets'] = math.log(data['total_assets'])
    
    # 로그 총부채 계산
    if 'total_liabilities' in data and data['total_liabilities'] is not None and data[
      'total_liabilities'] > 0:
      import math
      if 'log_total_liabilities' not in data or data['log_total_liabilities'] == 0:
        data['log_total_liabilities'] = math.log(data['total_liabilities'])
    
    return data
  
  def _format_financial_data_for_credit_rating(self, financial_data: Dict[str, Any]) -> str:
    """
    재무 데이터를 신용등급 평가를 위한 프롬프트 형식으로 포맷팅합니다.

    Args:
        financial_data (Dict[str, Any]): 재무 데이터

    Returns:
        str: 포맷팅된 재무 데이터 텍스트
    """
    # 단위 정보 확인
    unit = financial_data.get('unit', '원')
    
    # 단위 표준화 및 파생변수 계산
    financial_data = self._calculate_derived_metrics(financial_data)
    
    # 기본 재무 정보 포맷팅
    company_name = financial_data.get('company_name', '알 수 없음')
    
    # Alpaca 형식의 프롬프트 생성
    instruction = """다음 기업의 재무 정보를 분석하여 신용등급을 예측하세요.

신용등급은 반드시 다음 형식 중 하나만 사용해야 합니다:
AAA, AA+, AA, AA-, A+, A, A-, BBB+, BBB, BBB-, BB+, BB, BB-, B+, B, B-, CCC+, CCC, CCC-, CC+, CC, CC-, C+, C, C-, D

다른 형식(예: AAA+99+, AAA++, A++, BBB++, CCC--)은 사용하지 마세요."""
    
    # 입력 텍스트 생성
    input_text = f"재무 정보:\n"
    input_text += f"- 매출액: {financial_data.get('revenue', 0):,.0f}\n"
    input_text += f"- 영업이익: {financial_data.get('operating_profit', 0):,.0f}\n"
    input_text += f"- 순이익: {financial_data.get('net_income', 0):,.0f}\n"
    input_text += f"- 총자산: {financial_data.get('total_assets', 0):,.0f}\n"
    input_text += f"- 총부채: {financial_data.get('total_liabilities', 0):,.0f}\n"
    input_text += f"- 총자본: {financial_data.get('total_equity', 0):,.0f}\n"
    
    # 추가 재무 지표 (파인튜닝 테스트와 일치시키기 위함)
    if 'capital' in financial_data:
      input_text += f"- 자본금: {financial_data.get('capital', 0):,.0f}\n"
    if 'operating_cash_flow' in financial_data:
      input_text += f"- 영업현금흐름: {financial_data.get('operating_cash_flow', 0):,.0f}\n"
    if 'interest_bearing_debt' in financial_data:
      input_text += f"- 이자부담부채: {financial_data.get('interest_bearing_debt', 0):,.0f}\n"
    
    # 비율 지표
    if 'debt_ratio' in financial_data:
      input_text += f"- 부채비율: {financial_data.get('debt_ratio', 0):.2f}%\n"
    if 'ROA' in financial_data:
      input_text += f"- ROA: {financial_data.get('ROA', 0):.2f}%\n"
    if 'ROE' in financial_data:
      input_text += f"- ROE: {financial_data.get('ROE', 0):.2f}%\n"
    
    # 추가 비율 지표 (파인튜닝 테스트와 일치시키기 위함)
    if 'asset_turnover_ratio' in financial_data:
      input_text += f"- 자산회전율: {financial_data.get('asset_turnover_ratio', 0):.2f}\n"
    if 'interest_to_assets_ratio' in financial_data:
      input_text += f"- 이자/자산 비율: {financial_data.get('interest_to_assets_ratio', 0):.2f}\n"
    if 'interest_to_revenue_ratio' in financial_data:
      input_text += f"- 이자/매출 비율: {financial_data.get('interest_to_revenue_ratio', 0):.2f}\n"
    if 'cash_flow_to_interest' in financial_data:
      # null 값 처리
      cash_flow_to_interest = financial_data.get('cash_flow_to_interest')
      if cash_flow_to_interest is not None:
        input_text += f"- 현금흐름/이자 비율: {cash_flow_to_interest:.2f}\n"
      else:
        input_text += f"- 현금흐름/이자 비율: 0.00\n"
    if 'interest_to_cash_flow' in financial_data:
      # null 값 처리
      interest_to_cash_flow = financial_data.get('interest_to_cash_flow')
      if interest_to_cash_flow is not None:
        input_text += f"- 이자/현금흐름 비율: {interest_to_cash_flow:.2f}\n"
      else:
        input_text += f"- 이자/현금흐름 비율: 0.00\n"
    if 'log_total_assets' in financial_data:
      input_text += f"- 총자산(로그): {financial_data.get('log_total_assets', 0):.2f}\n"
    if 'log_total_liabilities' in financial_data:
      input_text += f"- 총부채(로그): {financial_data.get('log_total_liabilities', 0):.2f}\n"
    
    # positive_factors와 negative_factors 처리
    if 'positive_factors' in financial_data and financial_data['positive_factors'] is not None and \
        financial_data['positive_factors']:
      try:
        input_text += "\n신용등급 상향 요인:\n"
        if isinstance(financial_data['positive_factors'], str) and financial_data[
          'positive_factors'].startswith('['):
          factors = json.loads(financial_data['positive_factors'])
          for factor in factors:
            input_text += f"- {factor}\n"
        elif isinstance(financial_data['positive_factors'], list):
          for factor in financial_data['positive_factors']:
            input_text += f"- {factor}\n"
      except Exception as e:
        logger.error(f"긍정적 요소 파싱 오류: {str(e)}")
    
    if 'negative_factors' in financial_data and financial_data['negative_factors'] is not None and \
        financial_data['negative_factors']:
      try:
        input_text += "\n신용등급 하향 요인:\n"
        if isinstance(financial_data['negative_factors'], str) and financial_data[
          'negative_factors'].startswith('['):
          factors = json.loads(financial_data['negative_factors'])
          for factor in factors:
            input_text += f"- {factor}\n"
        elif isinstance(financial_data['negative_factors'], list):
          for factor in financial_data['negative_factors']:
            input_text += f"- {factor}\n"
      except Exception as e:
        logger.error(f"부정적 요소 파싱 오류: {str(e)}")
    
    # 추가 컨텍스트가 있으면 포함
    if 'additional_context' in financial_data and financial_data['additional_context']:
      input_text += f"\n추가 정보:\n{financial_data['additional_context']}\n"
    
    # Alpaca 형식으로 프롬프트 포맷팅
    alpaca_prompt = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{}

### Input:
{}

### Response:
"""
    
    formatted_text = alpaca_prompt.format(instruction, input_text)
    return formatted_text
  
  def _parse_credit_rating_response(self, response_text: str, company_name: str) -> Dict[str, Any]:
    """
    LLM 응답에서 신용등급 정보를 추출합니다.

    Args:
        response_text (str): LLM 응답 텍스트
        company_name (str): 회사명

    Returns:
        Dict[str, Any]: 추출된 신용등급 정보
    """
    # 기본 결과 구조
    result = {
      "company_name": company_name,
      "credit_rating": "N/A",
      "confidence_score": 0.0,
      "raw_response": response_text,
      "positive_factors": [],  # 신용등급 상향 요인
      "negative_factors": []  # 신용등급 하향 요인
    }
    
    try:
      # 유효한 신용등급 패턴 정의
      valid_ratings = [
        "AAA", "AA+", "AA", "AA-",
        "A+", "A", "A-",
        "BBB+", "BBB", "BBB-",
        "BB+", "BB", "BB-",
        "B+", "B", "B-",
        "CCC+", "CCC", "CCC-",
        "CC+", "CC", "CC-",
        "C+", "C", "C-",
        "D"
      ]
      
      # 신용등급 추출 (AAA, AA, A, BBB, BB, B, CCC, CC, C, D 형태)
      rating_pattern = r'신용등급[은는:\s]*([\w\+\-]+)'
      rating_match = re.search(rating_pattern, response_text)
      extracted_rating = None
      
      if rating_match:
        extracted_rating = rating_match.group(1).strip()
      else:
        # 다른 형태로 표현된 경우 (예: "A등급", "A+")
        alt_pattern = r'([A-D]{1,3}[\+\-]?)[\s]*등급'
        alt_match = re.search(alt_pattern, response_text)
        if alt_match:
          extracted_rating = alt_match.group(1).strip()
      
      # 추출된 신용등급이 유효한지 확인
      if extracted_rating:
        # 대소문자 구분 없이 비교하기 위해 대문자로 변환
        extracted_rating_upper = extracted_rating.upper()
        
        # 정확히 일치하는 등급이 있는지 확인
        if extracted_rating_upper in valid_ratings:
          result["credit_rating"] = extracted_rating_upper
        else:
          # 비정상적인 형식 처리
          # 기본 등급 추출 (A, AA, AAA, BBB 등)
          base_rating = re.match(r'([A-D]{1,3})', extracted_rating_upper)
          if base_rating:
            base = base_rating.group(1)
            # 기본 등급이 유효한지 확인
            if base in ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C", "D"]:
              # AAA는 특별 처리 - 항상 AAA로만 반환
              if base == "AAA":
                result["credit_rating"] = "AAA"
              else:
                # 다른 등급은 + 또는 - 기호 처리
                has_plus = "+" in extracted_rating_upper
                has_minus = "-" in extracted_rating_upper
                
                if has_plus:
                  result["credit_rating"] = f"{base}+"
                elif has_minus:
                  result["credit_rating"] = f"{base}-"
                else:
                  result["credit_rating"] = base
              
              logger.warning(
                f"비정상적인 신용등급 형식 '{extracted_rating}' 감지: '{result['credit_rating']}'로 변환")
            else:
              logger.warning(f"인식할 수 없는 신용등급 형식: {extracted_rating}. 기본값 'N/A' 사용.")
          else:
            logger.warning(f"인식할 수 없는 신용등급 형식: {extracted_rating}. 기본값 'N/A' 사용.")
      
      # 긍정적 요인 추출
      positive_section_patterns = [
        r'긍정적[인\s]*요인[:\s]*([\s\S]*?)(?:부정적|하향|약점|단점|리스크|$)',
        r'강점[:\s]*([\s\S]*?)(?:약점|단점|리스크|부정적|$)',
        r'상향\s*요인[:\s]*([\s\S]*?)(?:하향|부정적|약점|단점|리스크|$)'
      ]
      
      for pattern in positive_section_patterns:
        match = re.search(pattern, response_text)
        if match:
          positive_text = match.group(1).strip()
          # 항목별로 분리 (글머리 기호 또는 번호로 시작하는 라인)
          positive_items = re.findall(r'[-\*\d\.\s]+([^-\*\d\.\n][^\n]*)', positive_text)
          if positive_items:
            result["positive_factors"] = [item.strip() for item in positive_items if item.strip()]
          else:
            # 글머리 기호가 없는 경우 전체 텍스트를 하나의 요인으로 처리
            result["positive_factors"] = [positive_text]
          break
      
      # 부정적 요인 추출
      negative_section_patterns = [
        r'부정적[인\s]*요인[:\s]*([\s\S]*?)(?:긍정적|상향|강점|장점|$)',
        r'약점[:\s]*([\s\S]*?)(?:강점|장점|긍정적|$)',
        r'하향\s*요인[:\s]*([\s\S]*?)(?:상향|긍정적|강점|장점|$)',
        r'리스크[:\s]*([\s\S]*?)(?:기회|긍정적|강점|장점|$)'
      ]
      
      for pattern in negative_section_patterns:
        match = re.search(pattern, response_text)
        if match:
          negative_text = match.group(1).strip()
          # 항목별로 분리 (글머리 기호 또는 번호로 시작하는 라인)
          negative_items = re.findall(r'[-\*\d\.\s]+([^-\*\d\.\n][^\n]*)', negative_text)
          if negative_items:
            result["negative_factors"] = [item.strip() for item in negative_items if item.strip()]
          else:
            # 글머리 기호가 없는 경우 전체 텍스트를 하나의 요인으로 처리
            result["negative_factors"] = [negative_text]
          break
      
      # 신뢰도 점수 설정
      # 신용등급이 추출되었으면 높은 신뢰도, 아니면 낮은 신뢰도
      if result["credit_rating"] != "N/A":
        result["confidence_score"] = 0.9
      else:
        result["confidence_score"] = 0.5
    
    except Exception as e:
      logger.error(f"신용등급 응답 파싱 중 오류 발생: {str(e)}")
      # 오류 발생 시 기본값 유지
    
    return result
  
  async def _validate_with_agent(self, financial_data: Dict[str, Any], current_rating: str,
      validation_issues: List[str]) -> Dict[str, Any]:
    """
    LangGraph 에이전트를 사용하여 신용등급 검증을 수행합니다.

    Args:
        financial_data (Dict[str, Any]): 재무 데이터
        current_rating (str): 현재 신용등급
        validation_issues (List[str]): 검증 과정에서 발견된 이슈 목록

    Returns:
        Dict[str, Any]: 검증 결과 (final_rating, final_reason, is_adjusted)
    """
    if not self.agent:
      logger.warning("에이전트가 초기화되지 않아 검증을 건너뜁니다.")
      return {
        "final_rating": current_rating,
        "final_reason": "에이전트가 초기화되지 않아 검증을 건너뜁니다.",
        "is_adjusted": False
      }
    
    try:
      # 에이전트 실행 (최대 30초 대기)
      result = await asyncio.wait_for(
        self.agent.validate_rating(
          financial_data=financial_data,
          initial_rating=current_rating,
          validation_issues=validation_issues
        ),
        timeout=30  # 30초 타임아웃
      )
      
      return {
        "final_rating": result.get("final_rating", current_rating),
        "final_reason": result.get("reason", "에이전트 검증 완료"),
        "is_adjusted": result.get("is_adjusted", False)
      }
    
    except asyncio.TimeoutError:
      logger.warning("에이전트 검증이 시간 초과되었습니다. 원래 등급을 유지합니다.")
      return {
        "final_rating": current_rating,
        "final_reason": "에이전트 검증 시간 초과",
        "is_adjusted": False
      }
    except Exception as e:
      logger.error(f"에이전트 검증 중 오류: {str(e)}")
      return {
        "final_rating": current_rating,
        "final_reason": f"에이전트 검증 중 오류: {str(e)}",
        "is_adjusted": False
      }
  
  async def evaluate_credit_rating(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    재무 데이터를 기반으로 신용등급을 평가합니다.
    필요한 경우 Tavily 검색을 통해 긍정적/부정적 요소를 보강합니다.
    ML 모델 예측 후 룰 기반 검증 시스템을 통해 신용등급을 조정합니다.

    Args:
        financial_data (Dict[str, Any]): 재무 데이터

    Returns:
        Dict[str, Any]: 신용등급 평가 결과
    """
    try:
      company_name = financial_data.get('company_name', '알_수_없음')
      industry_name = financial_data.get('industry_name', None)
      
      # 긍정적/부정적 요소가 모두 없는 경우에만 Tavily 검색 수행
      has_positive_factors = ('positive_factors' in financial_data and
                              financial_data['positive_factors'] is not None and
                              financial_data['positive_factors'])
      has_negative_factors = ('negative_factors' in financial_data and
                              financial_data['negative_factors'] is not None and
                              financial_data['negative_factors'])
      
      # 둘 다 null인 경우에만 Tavily 검색 수행 (둘 중 하나라도 있으면 검색하지 않음)
      if not has_positive_factors and not has_negative_factors:
        logger.info(f"{company_name} 기업의 긍정적/부정적 요소가 모두 없어 Tavily 검색을 수행합니다.")
        search_results = await self.tavily_search_service.search_company_factors(company_name,
          industry_name)
        
        # 검색 결과가 있으면 financial_data에 추가
        if search_results["positive_factors"]:
          financial_data["positive_factors"] = search_results["positive_factors"]
          logger.info(f"Tavily 검색으로 {len(search_results['positive_factors'])}개의 긍정적 요소를 찾았습니다.")
        
        if search_results["negative_factors"]:
          financial_data["negative_factors"] = search_results["negative_factors"]
          logger.info(f"Tavily 검색으로 {len(search_results['negative_factors'])}개의 부정적 요소를 찾았습니다.")
      
      # 프롬프트 생성
      prompt = self._format_financial_data_for_credit_rating(financial_data)
      
      # 프롬프트 로깅
      unit = financial_data.get('unit', '원')
      log_to_file(prompt, 'prompt', 'credit_rating', company_name, unit)
      
      # LLM 요청
      response = await self.llm_manager.request(prompt)
      
      # 응답 로깅
      log_to_file(response, 'response', 'credit_rating', company_name, unit)
      
      # 응답 파싱
      result = self._parse_credit_rating_response(response, company_name)
      
      # 파싱된 결과에 긍정적/부정적 요소가 없으면 Tavily 검색 결과 사용
      if not result["positive_factors"] and 'positive_factors' in financial_data and financial_data[
        'positive_factors']:
        if isinstance(financial_data['positive_factors'], str) and financial_data[
          'positive_factors'].startswith('['):
          try:
            result["positive_factors"] = json.loads(financial_data['positive_factors'])
          except:
            pass
        elif isinstance(financial_data['positive_factors'], list):
          result["positive_factors"] = financial_data['positive_factors']
      
      if not result["negative_factors"] and 'negative_factors' in financial_data and financial_data[
        'negative_factors']:
        if isinstance(financial_data['negative_factors'], str) and financial_data[
          'negative_factors'].startswith('['):
          try:
            result["negative_factors"] = json.loads(financial_data['negative_factors'])
          except:
            pass
        elif isinstance(financial_data['negative_factors'], list):
          result["negative_factors"] = financial_data['negative_factors']
      
      # 룰 기반 검증 시스템 적용
      logger.info(f"{company_name} 기업의 ML 예측 신용등급: {result['credit_rating']}")
      
      # 원본 ML 예측 결과 저장
      result["ml_predicted_rating"] = result["credit_rating"]
      
      # 룰 기반 검증 및 조정
      adjusted_rating, adjustment_reason = comprehensive_credit_validation(financial_data,
        result["credit_rating"])
      
      # 에이전트 검증이 필요한지 확인
      needs_agent_validation = True
      
      # 명확한 케이스 확인 (에이전트 검증 생략) - 조건 완화
      if adjusted_rating in ['D']:
        needs_agent_validation = False
        logger.info(f"{company_name} 기업은 명확한 케이스로 에이전트 검증을 건너뜁니다.")
      elif financial_data.get('total_equity', 1) <= 0:
        needs_agent_validation = False
        logger.info(f"{company_name} 기업은 완전 자본잠식 상태로 에이전트 검증을 건너뜁니다.")
      elif financial_data.get('total_liabilities', 0) > financial_data.get('total_assets', 0):
        needs_agent_validation = False
        logger.info(f"{company_name} 기업은 부채가 자산을 초과하여 에이전트 검증을 건너뜁니다.")
      elif (financial_data.get('operating_cash_flow', 0) < 0 and
            financial_data.get('interest_expense', 0) > 0 and
            abs(financial_data['operating_cash_flow']) > financial_data['interest_expense']):
        needs_agent_validation = False
        logger.info(f"{company_name} 기업은 현금흐름 악화로 인해 에이전트 검증을 건너뜁니다.")
      # AAA 등급 조건 대폭 완화
      elif adjusted_rating == 'AAA' and \
          financial_data.get('debt_ratio', 0) < 0.5 and \
          financial_data.get('current_ratio', 0) > 1.2 and \
          financial_data.get('operating_profit_margin', 0) > 0.08:
        needs_agent_validation = False
        logger.info(f"{company_name} 기업은 매우 우량한 AAA 등급으로 에이전트 검증을 건너뜁니다.")
        logger.info(
          f"조건 확인 - 부채비율: {financial_data.get('debt_ratio', 0):.3f}, 유동비율: {financial_data.get('current_ratio', 0):.2f}, 영업이익률: {financial_data.get('operating_profit_margin', 0):.3f}")
      
      # 에이전트 검증 실행
      if needs_agent_validation:
        agent_result = await self.credit_rating_agent.validate_rating(
          financial_data=financial_data,
          initial_rating=adjusted_rating,
          validation_issues=[adjustment_reason] if adjustment_reason else []
        )
        
        final_rating = agent_result.get("final_rating", adjusted_rating)
        final_reason = agent_result.get("final_reason", "")
        is_adjusted = agent_result.get("is_adjusted", False)
        
        # 에이전트가 등급을 조정한 경우
        if is_adjusted and final_rating != adjusted_rating:
          logger.info(f"에이전트가 등급을 조정했습니다: {adjusted_rating} -> {final_rating}")
          adjusted_rating = final_rating
          adjustment_reason = f"{adjustment_reason}\n에이전트 조정: {final_reason}"
      
      # 최종 결과 반영
      result["credit_rating"] = adjusted_rating
      result["adjustment_reason"] = adjustment_reason
      result["agent_validation_skipped"] = not needs_agent_validation
      
      # 조정 결과 로깅
      if result["ml_predicted_rating"] != result["credit_rating"]:
        logger.info(
          f"{company_name} 기업의 신용등급 조정: {result['ml_predicted_rating']} -> {result['credit_rating']}")
        logger.info(f"조정 사유: {adjustment_reason}")
        
        # 부정적 요소에 조정 사유 추가
        if adjustment_reason and "사유:" in adjustment_reason:
          reasons = adjustment_reason.split("사유:")[1].strip()
          if reasons:
            reason_list = [r.strip() for r in reasons.split(",")]
            if isinstance(result["negative_factors"], list):
              result["negative_factors"].extend(reason_list)
            else:
              result["negative_factors"] = reason_list
      
      return result
    except Exception as e:
      logger.error(f"신용등급 평가 중 오류 발생: {str(e)}")
      raise ValueError(f"신용등급 평가 중 오류 발생: {str(e)}")
  
  async def submit_credit_rating_request(self, company_name: str, financial_data: Dict[str, Any],
      additional_context: Optional[str] = None) -> str:
    """
    신용등급 평가 요청을 제출하고 요청 ID를 반환합니다.

    Args:
        company_name (str): 회사명
        financial_data (Dict[str, Any]): 재무 데이터
        additional_context (Optional[str], optional): 추가 컨텍스트. 기본값은 None.

    Returns:
        str: 요청 ID
    """
    # 프롬프트 생성
    instruction = "다음 재무 정보를 바탕으로 기업의 신용등급을 평가해주세요."
    input_text = self._format_financial_data_for_credit_rating(financial_data)
    if additional_context:
      input_text += f"\n\n추가 정보: {additional_context}"
    
    # 비동기 요청 제출
    request_id = await self.llm_manager.submit_request(instruction, input_text)
    return request_id
