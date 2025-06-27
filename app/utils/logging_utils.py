"""
로깅 관련 유틸리티 함수
"""
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)


def log_to_file(content: str, 
                log_type: str, 
                module_name: str, 
                company_name: str, 
                unit: str = '억원',
                file_prefix: str = '') -> str:
    """
    내용을 파일에 로깅합니다.

    Args:
        content (str): 로깅할 내용
        log_type (str): 로그 유형 (예: 'prompt', 'response')
        module_name (str): 모듈 이름 (예: 'credit_rating', 'report_generation')
        company_name (str): 회사명
        unit (str, optional): 데이터 단위. 기본값은 '억원'.
        file_prefix (str, optional): 파일명 접두사. 기본값은 빈 문자열.

    Returns:
        str: 로그 파일 경로
    """
    # 타임스탬프 생성
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    # 로그 디렉토리 구조 생성
    base_log_dir = os.path.join(os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
    module_log_dir = os.path.join(base_log_dir, module_name)
    log_type_dir = os.path.join(module_log_dir, f"{log_type}s")
    os.makedirs(log_type_dir, exist_ok=True)
    
    # 파일명 생성
    prefix = f"{file_prefix}_" if file_prefix else ""
    log_file = os.path.join(log_type_dir,
                           f"{prefix}{module_name}_{log_type}_{company_name}_{unit}_{timestamp}.txt")
    
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"{module_name} {log_type}가 {log_file}에 저장되었습니다.")
        return log_file
    except Exception as e:
        logger.error(f"{log_type} 로깅 중 오류 발생: {str(e)}")
        return ""
