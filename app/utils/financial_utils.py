"""
재무 데이터 관련 유틸리티 함수
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def normalize_unit(financial_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    재무 데이터의 단위를 표준화합니다.
    입력 데이터가 원 단위인 경우 억원 단위로 변환합니다.

    Args:
        financial_data (Dict[str, Any]): 재무 데이터

    Returns:
        Dict[str, Any]: 단위가 표준화된 재무 데이터
    """
    # 딕셔너리 복사하여 원본 데이터 보존
    data = financial_data.copy()

    # 단위 확인 및 변환 (revenue 값을 기준으로 판단)
    # 일반적으로 revenue가 100억 이상이면 원 단위, 100 이하면 억원 단위로 가정
    if 'revenue' in data and data['revenue'] is not None:
        if data['revenue'] > 10000000000:  # 100억 이상이면 원 단위로 가정
            # 원 단위를 억원 단위로 변환
            for key in ['revenue', 'operating_profit', 'net_income', 'total_assets',
                        'total_liabilities', 'total_equity', 'capital',
                        'operating_cash_flow', 'interest_bearing_debt']:
                if key in data and data[key] is not None:
                    data[key] = data[key] / 100000000  # 1억으로 나누어 억원 단위로 변환

            logger.info("재무 데이터가 원 단위로 입력되어 억원 단위로 변환되었습니다.")

    return data
