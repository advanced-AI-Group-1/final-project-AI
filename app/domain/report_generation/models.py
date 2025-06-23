from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from pydantic import BaseModel


@dataclass
class RealFinancialData:
  """실제 재무제표 데이터 (1년 기준)"""
  corp_name: str  # 기업명
  market_type: str  # 시장구분 (KOSPI, KOSDAQ 등)
  industry_name: str  # 업종명

  # 손익계산서
  revenue: float  # 매출액
  operating_profit: float  # 영업이익
  net_income: float  # 당기순이익

  # 재무상태표
  total_assets: float  # 총자산
  total_liabilities: float  # 총부채
  total_equity: float  # 자본총계
  capital: float  # 자본금
  interest_bearing_debt: float  # 이자발생부채

  # 현금흐름표
  operating_cash_flow: float  # 영업활동현금흐름

  # 이미 계산된 재무비율들
  debt_ratio: float  # 부채비율
  roa: float  # ROA
  roe: float  # ROE
  asset_turnover_ratio: float  # 매출총자산회전율
  interest_to_assets_ratio: float  # 이자총자산비율
  interest_to_revenue_ratio: float  # 이자매출비율
  cash_flow_to_interest: float  # 현금흐름대비이자
  interest_to_cash_flow: float  # 이자대비현금흐름
  log_total_assets: float  # 로그총자산
  log_total_liabilities: float  # 로그총부채
  is_consolidated: Optional[str] = None  # 연결재무제표 여부


@dataclass
class CreditRating:
  """신용등급 정보"""
  rating: str  # 현재 등급
  outlook: str  # 전망
  financial_strength: str  # 재무 건전성
  business_risk: str  # 사업 위험
  industry_outlook: str  # 산업 전망
  confidence_score: float  # 신뢰도 점수


@dataclass
class Section:
  """보고서 섹션"""
  name: str
  description: str
  requires_calculation: bool  # 추가 재무비율 계산 필요 여부
  requires_research: bool  # 웹 검색 필요 여부
  content: str = ""
  char_limit: int = 0  # 글자 수 제한


class ReportState(BaseModel):
  """보고서 생성 상태"""
  company_data: Dict[str, Any]  # 기업 데이터
  credit_rating: Dict[str, Any]  # 신용등급 정보
  sections: List[Dict[str, Any]]  # 보고서 섹션
  additional_ratios: Dict[str, float] = {}  # 추가 계산된 비율들
  summary_card: str = ""  # 1페이지 요약 카드
  detailed_report: str = ""  # 상세 풀 리포트
  current_section_index: int = 0
  all_analysis_done: bool = False
  next: Optional[str] = None  # LangGraph 워크플로우에서 다음 노드를 지정하기 위한 필드
  review_results: List[Dict[str, Any]] = []  # 섹션 검증 결과
  sections_to_regenerate: List[int] = []  # 재생성이 필요한 섹션 인덱스 목록
  regeneration_mode: bool = False  # 재생성 모드 여부
  
  # 딕셔너리처럼 접근할 수 있도록 메서드 추가
  def __getitem__(self, key):
      return getattr(self, key)
      
  def __setitem__(self, key, value):
      setattr(self, key, value)
      
  # 딕셔너리의 get 메서드 구현
  def get(self, key, default=None):
      try:
          return getattr(self, key)
      except AttributeError:
          return default


class AdditionalRatioCalculator:
  """기존 재무비율 외 추가 비율 계산"""

  @staticmethod
  def calculate_liquidity_ratios(data: Dict[str, Any]) -> Dict[str, float]:
    """유동성 비율 (추정 계산)"""
    ratios = {}

    # 유동자산/유동부채가 없으므로 추정
    estimated_current_assets = data["total_assets"] * 0.5  # 50% 추정
    estimated_current_liabilities = data["total_liabilities"] * 0.7  # 70% 추정

    if estimated_current_liabilities > 0:
      ratios['estimated_current_ratio'] = estimated_current_assets / estimated_current_liabilities

    # 현금비율 (영업현금흐름 기반 추정)
    if estimated_current_liabilities > 0 and "operating_cash_flow" in data:
      ratios['cash_flow_ratio'] = data["operating_cash_flow"] / estimated_current_liabilities

    return ratios

  @staticmethod
  def calculate_coverage_ratios(data: Dict[str, Any]) -> Dict[str, float]:
    """커버리지 비율"""
    ratios = {}

    # 이자보상배수 (이자비용 = 이자매출비율 × 매출액)
    if "interest_to_revenue_ratio" in data and data["interest_to_revenue_ratio"] > 0:
      interest_expense = data["interest_to_revenue_ratio"] * data["revenue"] / 100
      if interest_expense > 0:
        ratios['interest_coverage_ratio'] = data["operating_profit"] / interest_expense
        ratios['ebitda_interest_coverage'] = (data["operating_profit"] * 1.3) / interest_expense  # EBITDA 추정

      # 현금흐름 이자보상배수
      if "operating_cash_flow" in data:
        ratios['cash_interest_coverage'] = data["operating_cash_flow"] / interest_expense

    return ratios

  @staticmethod
  def calculate_all_additional_ratios(data: Dict[str, Any]) -> Dict[str, float]:
    """모든 추가 재무비율 계산"""
    all_ratios = {}

    liquidity = AdditionalRatioCalculator.calculate_liquidity_ratios(data)
    coverage = AdditionalRatioCalculator.calculate_coverage_ratios(data)

    all_ratios.update(liquidity)
    all_ratios.update(coverage)

    return all_ratios
