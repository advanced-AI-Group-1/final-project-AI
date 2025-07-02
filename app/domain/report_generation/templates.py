"""
보고서 생성에 필요한 마크다운 변환 기능을 제공하는 모듈
"""
import re
from datetime import datetime
from typing import Dict, Any, Optional, List

def format_report_data(company_name: str, summary_card: str, detailed_report: str,
    generated_at: str) -> Dict[str, Any]:
  """
  보고서 데이터를 JSON 형식으로 포맷팅합니다.
  프론트엔드에서 마크다운을 HTML로 변환하도록 변경되었습니다.
  """
  generation_date = generated_at.split("T")[0].replace("-", "년 ", 1).replace("-", "월 ", 1) + "일"
  
  # 업종 및 시장 정보가 없는 경우 기본값 설정
  industry_name = "금융 분석"
  market_type = "신용평가"
  
  # 보고서 데이터를 딕셔너리로 구성
  report_data = {
    "company_name": company_name,
    "subtitle": f"{industry_name} | {market_type}",
    "summary_content": summary_card,  # 마크다운 그대로 전달
    "detailed_content": detailed_report,  # 마크다운 그대로 전달
    "generation_date": generation_date,
    "industry_name": industry_name,
    "market_type": market_type
  }
  
  return report_data
