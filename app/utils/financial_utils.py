"""
재무 데이터 관련 유틸리티 함수
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def normalize_unit(financial_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    재무 데이터의 단위를 표준화합니다.
    모든 재무 데이터는 '원' 단위로 통일됩니다.

    Args:
        financial_data (Dict[str, Any]): 재무 데이터

    Returns:
        Dict[str, Any]: 단위가 표준화된 재무 데이터
    """
    # 딕셔너리 복사하여 원본 데이터 보존
    data = financial_data.copy()
    
    # 단위 정보가 없는 경우 기본값 설정
    if 'unit' not in data:
        data['unit'] = '원'
    else:
        # 단위 정보를 '원'으로 통일
        data['unit'] = '원'
    
    return data
