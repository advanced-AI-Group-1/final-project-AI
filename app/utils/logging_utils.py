"""
로깅 관련 유틸리티 함수
"""
import logging
import os
import time
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)

# 메모리에 로그를 저장하기 위한 딕셔너리
# 키: (module_name, company_name), 값: [(log_type, content, file_prefix, unit, timestamp), ...]
in_memory_logs: Dict[Tuple[str, str], List[Tuple[str, str, str, str, str]]] = {}

# 노드별 로그를 저장하기 위한 딕셔너리
# 키: (module_name, company_name), 값: [(node_name, content, timestamp), ...]
node_logs: Dict[Tuple[str, str], List[Tuple[str, str, str]]] = {}


def log_to_memory(content: str,
                log_type: str,
                module_name: str,
                company_name: str,
                unit: str = '억원',
                file_prefix: str = '') -> None:
    """
    내용을 메모리에 로깅합니다.

    Args:
        content (str): 로깅할 내용
        log_type (str): 로그 유형 (예: 'prompt', 'response')
        module_name (str): 모듈 이름 (예: 'credit_rating', 'report_generation')
        company_name (str): 회사명
        unit (str, optional): 데이터 단위. 기본값은 '억원'.
        file_prefix (str, optional): 파일명 접두사. 기본값은 빈 문자열.
    """
    # 타임스탬프 생성
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    # 메모리에 로그 저장
    key = (module_name, company_name)
    if key not in in_memory_logs:
        in_memory_logs[key] = []
    
    in_memory_logs[key].append((log_type, content, file_prefix, unit, timestamp))
    
    # 콘솔 로그 출력을 제거하고 디버그 레벨로만 남깁니다
    if log_type in ['prompt', 'response']:
        # 프롬프트와 응답 로그는 디버그 레벨로만 출력 (일반적으로 표시되지 않음)
        logger.debug(f"{module_name} {log_type} 메모리에 저장됨 (회사: {company_name})")
    else:
        # 다른 유형의 로그는 정보 레벨로 유지
        logger.info(f"{module_name} {log_type} 메모리에 저장됨 (회사: {company_name})")


def log_node_to_memory(node_name: str,
                      content: str,
                      module_name: str,
                      company_name: str) -> None:
    """
    노드의 결과를 메모리에 로깅합니다.

    Args:
        node_name (str): 노드 이름 (예: 'plan_sections', 'analyze_section')
        content (str): 로깅할 내용
        module_name (str): 모듈 이름 (예: 'report_agent')
        company_name (str): 회사명
    """
    # 타임스탬프 생성
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    # 메모리에 노드 로그 저장
    key = (module_name, company_name)
    if key not in node_logs:
        node_logs[key] = []
    
    node_logs[key].append((node_name, content, timestamp))
    
    # 로그 출력
    logger.info(f"{module_name} 노드 '{node_name}' 결과가 메모리에 저장됨 (회사: {company_name})")


def save_logs_to_files(module_name: str, company_name: str) -> List[str]:
    """
    특정 모듈과 회사에 대한 모든 메모리 로그를 파일로 저장합니다.

    Args:
        module_name (str): 모듈 이름
        company_name (str): 회사명

    Returns:
        List[str]: 저장된 로그 파일 경로 목록
    """
    key = (module_name, company_name)
    if key not in in_memory_logs:
        logger.info(f"{module_name}에 대한 {company_name}의 저장할 로그가 없습니다.")
        return []
    
    saved_files = []
    
    # 로그 디렉토리 구조 생성
    base_log_dir = os.path.join(os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
    module_log_dir = os.path.join(base_log_dir, module_name)
    
    # 각 로그 항목에 대해 파일 저장
    for log_type, content, file_prefix, unit, timestamp in in_memory_logs[key]:
        log_type_dir = os.path.join(module_log_dir, f"{log_type}s")
        os.makedirs(log_type_dir, exist_ok=True)
        
        # 파일명 생성
        prefix = f"{file_prefix}_" if file_prefix else ""
        log_file = os.path.join(log_type_dir,
                            f"{prefix}{module_name}_{log_type}_{company_name}_{unit}_{timestamp}.txt")
        
        try:
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(content)
            saved_files.append(log_file)
        except Exception as e:
            logger.error(f"{log_type} 로깅 중 오류 발생: {str(e)}")
    
    # 저장 후 메모리에서 해당 로그 삭제
    if saved_files:
        logger.info(f"{module_name}에 대한 {company_name}의 로그 {len(saved_files)}개가 파일로 저장되었습니다.")
        del in_memory_logs[key]
    
    return saved_files


def save_node_logs_to_file(module_name: str, company_name: str, unit: str = '억원') -> str:
    """
    특정 모듈과 회사에 대한 모든 노드 로그를 하나의 파일로 저장합니다.

    Args:
        module_name (str): 모듈 이름
        company_name (str): 회사명
        unit (str, optional): 데이터 단위. 기본값은 '억원'.

    Returns:
        str: 저장된 로그 파일 경로
    """
    key = (module_name, company_name)
    if key not in node_logs or not node_logs[key]:
        logger.info(f"{module_name}에 대한 {company_name}의 저장할 노드 로그가 없습니다.")
        return ""
    
    # 타임스탬프 생성
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    # 로그 디렉토리 구조 생성
    base_log_dir = os.path.join(os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
    module_log_dir = os.path.join(base_log_dir, module_name)
    reports_dir = os.path.join(module_log_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    # 파일명 생성
    log_file = os.path.join(reports_dir,
                        f"agent_based_report_generation_report_{company_name}_{unit}_{timestamp}.txt")
    
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            # 노드 로그를 시간순으로 정렬
            sorted_logs = sorted(node_logs[key], key=lambda x: x[2])
            
            for node_name, content, _ in sorted_logs:
                # 노드 구분선 추가
                f.write(f"\n{'=' * 80}\n")
                f.write(f"노드: {node_name}\n")
                f.write(f"{'=' * 80}\n\n")
                f.write(content)
                f.write("\n\n")
        
        logger.info(f"{module_name}에 대한 {company_name}의 모든 노드 로그가 {log_file}에 저장되었습니다.")
        
        # 저장 후 메모리에서 해당 로그 삭제
        del node_logs[key]
        
        return log_file
    except Exception as e:
        logger.error(f"노드 로그 저장 중 오류 발생: {str(e)}")
        return ""


def log_node_to_file(node_name: str,
                    content: str,
                    module_name: str,
                    company_name: str,
                    unit: str = '억원') -> str:
    """
    노드의 결과를 바로 파일에 로깅합니다.

    Args:
        node_name (str): 노드 이름 (예: 'plan_sections', 'analyze_section')
        content (str): 로깅할 내용
        module_name (str): 모듈 이름 (예: 'report_agent')
        company_name (str): 회사명
        unit (str, optional): 데이터 단위. 기본값은 '억원'.

    Returns:
        str: 로그 파일 경로
    """
    # 타임스탬프 생성
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    # 로그 디렉토리 구조 생성
    base_log_dir = os.path.join(os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
    module_log_dir = os.path.join(base_log_dir, module_name)
    nodes_dir = os.path.join(module_log_dir, "nodes")
    os.makedirs(nodes_dir, exist_ok=True)
    
    # 파일명 생성
    log_file = os.path.join(nodes_dir,
                        f"{module_name}_node_{node_name}_{company_name}_{unit}_{timestamp}.txt")
    
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"{module_name} 노드 '{node_name}'의 결과가 {log_file}에 저장되었습니다.")
        return log_file
    except Exception as e:
        logger.error(f"노드 '{node_name}' 로깅 중 오류 발생: {str(e)}")
        return ""


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
