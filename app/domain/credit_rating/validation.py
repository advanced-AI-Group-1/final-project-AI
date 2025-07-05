"""
신용등급 평가 결과를 검증하고 조정하는 룰 기반 시스템
"""
import logging
from typing import Dict, Any, Tuple, List, Optional

logger = logging.getLogger(__name__)


def check_capital_impairment(data: Dict[str, Any]) -> Optional[Tuple[str, str]]:
  """
  자본잠식 상태 확인
  
  Args:
      data: 재무 데이터
      
  Returns:
      Tuple[str, str]: 조정된 등급과 사유, 문제가 없으면 None
  """
  # 완전 자본잠식
  if data.get('total_equity', 0) <= 0:
    return 'D', "완전 자본잠식 상태"
  
  # 50% 이상 자본잠식 (자본금 대비 자본총계 비율)
  if data.get('capital', 0) > 0 and data.get('total_equity', 0) / data.get('capital', 1) < 0.5:
    return 'C', "심각한 자본잠식 (자본금 대비 자본총계 50% 미만)"
  
  return None


def check_liquidity_crisis(data: Dict[str, Any]) -> Optional[Tuple[str, str]]:
  """
  유동성 위기 확인
  
  Args:
      data: 재무 데이터
      
  Returns:
      Tuple[str, str]: 조정된 등급과 사유, 문제가 없으면 None
  """
  # 영업현금흐름이 이자비용을 커버 못함
  if data.get('operating_cash_flow', 0) < 0 and data.get('interest_bearing_debt', 0) > 0:
    if abs(data.get('operating_cash_flow', 0)) > data.get('interest_bearing_debt', 1) * 0.05:
      return 'D', "영업현금흐름 부족으로 이자지급 불가능"
  
  # 부채가 자산을 초과
  if data.get('total_liabilities', 0) > data.get('total_assets', 0):
    return 'D', "부채가 자산 초과"
  
  return None


def check_profitability_risk(data: Dict[str, Any]) -> Tuple[int, List[str]]:
  """
  수익성 위험 확인
  
  Args:
      data: 재무 데이터
      
  Returns:
      Tuple[int, List[str]]: 위험 점수와 사유 목록
  """
  risk_score = 0
  reasons = []
  
  # 연속 적자 (영업손실 + 순손실)
  if data.get('operating_profit', 0) < 0 and data.get('net_income', 0) < 0:
    risk_score += 3
    reasons.append("영업손실과 순손실 동시 발생")
  
  # 극단적 ROA
  if data.get('ROA', 0) < -0.2:
    risk_score += 2
    reasons.append("ROA가 -20% 이하")
  
  # 매출 대비 이자비용 과다
  if data.get('interest_to_revenue_ratio', 0) > 0.3:
    risk_score += 2
    reasons.append("매출 대비 이자비용 30% 초과")
  
  return risk_score, reasons


def check_debt_risk(data: Dict[str, Any]) -> Tuple[int, List[str]]:
  """
  부채 위험 확인
  
  Args:
      data: 재무 데이터
      
  Returns:
      Tuple[int, List[str]]: 위험 점수와 사유 목록
  """
  risk_score = 0
  reasons = []
  
  # 부채비율 극단치
  if data.get('debt_ratio', 0) > 5:
    risk_score += 3
    reasons.append("부채비율이 500% 초과")
  elif data.get('debt_ratio', 0) > 3:
    risk_score += 2
    reasons.append("부채비율이 300% 초과")
  
  # 이자보상비율 위험
  if data.get('operating_profit', 0) > 0 and data.get('interest_bearing_debt', 0) > 0:
    interest_coverage = data.get('operating_profit', 0) / (
          data.get('interest_bearing_debt', 1) * 0.05)  # 가정 이자율 5%
    if interest_coverage < 1:
      risk_score += 3
      reasons.append("이자보상비율 1배 미만")
    elif interest_coverage < 2:
      risk_score += 1
      reasons.append("이자보상비율 2배 미만")
  
  return risk_score, reasons


def check_manufacturing_specific(data: Dict[str, Any]) -> Tuple[int, List[str]]:
  """
  제조업 특화 검증
  
  Args:
      data: 재무 데이터
      
  Returns:
      Tuple[int, List[str]]: 위험 점수와 사유 목록
  """
  if data.get('industry_name', '') in ['전자 부품 제조업', '기계 제조업', '자동차 제조업']:
    risk_score = 0
    reasons = []
    
    # 자산회전율이 너무 높음 (매출 축소 가능성)
    if data.get('asset_turnover_ratio', 0) > 5:
      risk_score += 1
      reasons.append("자산회전율 과도히 높음 - 자산 축소 가능성")
    
    # 재고 관련 위험 (간접 추정)
    if data.get('net_income', 0) > 0 and data.get('operating_cash_flow', 0) < data.get('net_income',
        1) * 0.5:
      risk_score += 1
      reasons.append("영업현금흐름이 순이익 대비 과도히 낮음")
    
    return risk_score, reasons
  
  return 0, []


def check_market_conditions(data: Dict[str, Any]) -> Tuple[int, List[str]]:
  """
  시장 상황 반영
  
  Args:
      data: 재무 데이터
      
  Returns:
      Tuple[int, List[str]]: 위험 점수와 사유 목록
  """
  risk_score = 0
  reasons = []
  
  # 기타법인의 경우 추가 위험
  if data.get('market_type', '') == '기타법인':
    risk_score += 1
    reasons.append("비상장 기업으로 유동성 위험 추가")
  
  return risk_score, reasons


def check_size_risk(data: Dict[str, Any]) -> Tuple[int, List[str]]:
  """
  규모별 위험도
  
  Args:
      data: 재무 데이터
      
  Returns:
      Tuple[int, List[str]]: 위험 점수와 사유 목록
  """
  risk_score = 0
  reasons = []
  
  # 소규모 기업 위험
  if data.get('total_assets', 0) < 100:  # 100억 미만
    if data.get('debt_ratio', 0) > 2:
      risk_score += 2
      reasons.append("소규모 기업의 높은 부채비율")
  
  return risk_score, reasons


def comprehensive_credit_validation(financial_data: Dict[str, Any], ml_prediction: str) -> Tuple[
  str, str]:
  """
  종합적인 신용등급 검증 시스템
  
  Args:
      financial_data: 재무 데이터
      ml_prediction: ML 모델이 예측한 신용등급
      
  Returns:
      Tuple[str, str]: 조정된 신용등급과 조정 사유
  """
  # 등급 매핑
  rating_to_score = {
    'AAA': 10, 'AA+': 9, 'AA': 8, 'AA-': 7,
    'A+': 6, 'A': 5, 'A-': 4,
    'BBB+': 3, 'BBB': 2, 'BBB-': 1,
    'BB+': 0, 'BB': -1, 'BB-': -2,
    'B+': -3, 'B': -4, 'B-': -5,
    'CCC+': -6, 'CCC': -7, 'CCC-': -8,
    'CC+': -9, 'CC': -10, 'CC-': -11,
    'C+': -12, 'C': -13, 'C-': -14,
    'D': -15
  }
  
  score_to_rating = {v: k for k, v in rating_to_score.items()}
  
  # ML 예측 등급이 유효하지 않은 경우 기본값 설정
  if ml_prediction not in rating_to_score:
    logger.warning(f"유효하지 않은 신용등급: {ml_prediction}, 기본값 'BBB'로 설정")
    ml_prediction = 'BBB'
  
  original_score = rating_to_score[ml_prediction]
  final_score = original_score
  all_reasons = []
  
  # 1. 치명적 위험 체크
  fatal_check = check_capital_impairment(financial_data)
  if fatal_check:
    logger.info(f"치명적 위험 감지: {fatal_check[1]}")
    return fatal_check[0], f"치명적 위험: {fatal_check[1]}"
  
  liquidity_check = check_liquidity_crisis(financial_data)
  if liquidity_check:
    logger.info(f"유동성 위기 감지: {liquidity_check[1]}")
    return liquidity_check[0], f"유동성 위기: {liquidity_check[1]}"
  
  # 2. 위험 점수 누적
  profit_risk, profit_reasons = check_profitability_risk(financial_data)
  debt_risk, debt_reasons = check_debt_risk(financial_data)
  industry_risk, industry_reasons = check_manufacturing_specific(financial_data)
  market_risk, market_reasons = check_market_conditions(financial_data)
  size_risk, size_reasons = check_size_risk(financial_data)
  
  total_risk = profit_risk + debt_risk + industry_risk + market_risk + size_risk
  all_reasons.extend(
    profit_reasons + debt_reasons + industry_reasons + market_reasons + size_reasons)
  
  # 3. 등급 조정
  final_score = original_score - total_risk
  
  # 점수를 등급 범위 내로 제한
  final_score = max(-15, min(10, final_score))
  
  # 4. 최종 검증
  adjusted_rating = score_to_rating[final_score]
  
  # 5. 조정 사유 정리
  if final_score < original_score:
    adjustment_reason = f"Runpod 예측({ml_prediction})에서 {adjusted_rating}로 하향조정. 사유: {', '.join(all_reasons)}"
    logger.info(f"신용등급 하향 조정: {ml_prediction} -> {adjusted_rating}")
  else:
    adjustment_reason = f"Runpod 예측({ml_prediction}) 유지"
    logger.info(f"신용등급 유지: {ml_prediction}")
  
  return adjusted_rating, adjustment_reason
