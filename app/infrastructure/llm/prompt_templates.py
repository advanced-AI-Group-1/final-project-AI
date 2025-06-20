"""
LLM 프롬프트 템플릿 모음
"""

# Alpaca 프롬프트 템플릿
ALPACA_PROMPT_TEMPLATE = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{}

### Input:
{}

### Response:
"""


def format_financial_data_for_credit_rating(financial_data):
  """
    신용등급 평가를 위해 재무 데이터를 포맷팅합니다.
    
    Args:
        financial_data (Dict): 재무 데이터 딕셔너리
        
    Returns:
        str: 포맷팅된 재무 정보 텍스트
    """
  # 필요한 키가 없는 경우 기본값 사용
  formatted_text = f"""재무 정보:"""

  # 기본 재무 지표 (영어 키 사용)
  basic_metrics = [('Revenue', 'revenue', ','), ('Operating Profit', 'operating_profit', ','),
                   ('Net Income', 'net_income', ','), ('Total Assets', 'total_assets', ','),
                   ('Total Liabilities', 'total_liabilities', ','), ('Total Equity', 'total_equity', ','),
                   ('Capital', 'capital', ',')]

  # 비율 지표 (영어 키 사용)
  ratio_metrics = [('Debt Ratio', 'debt_ratio', '.2f'), ('ROA', 'ROA', '.2f'), ('ROE', 'ROE', '.2f'),
                   ('Asset Turnover Ratio', 'asset_turnover_ratio', '.2f')]

  # 파생 변수 (영어 키 사용)
  derived_metrics = [('Interest to Assets Ratio', 'interest_to_assets_ratio', '.2f'),
                     ('Interest to Revenue Ratio', 'interest_to_revenue_ratio', '.2f'),
                     ('Cash Flow to Interest', 'cash_flow_to_interest', '.2f'),
                     ('Interest to Cash Flow', 'interest_to_cash_flow', '.2f'),
                     ('Operating Cash Flow', 'operating_cash_flow', ','),
                     ('Interest Bearing Debt', 'interest_bearing_debt', ',')]

  # 기본 재무 지표 포맷팅
  for label, key, format_type in basic_metrics:
    if key in financial_data and financial_data[key] is not None:
      value = financial_data[key]
      if format_type == ',':
        formatted_text += f"\n- {label}: {value:,.0f}"
      else:
        formatted_text += f"\n- {label}: {value}"
    elif key in financial_data:
      formatted_text += f"\n- {label}: 데이터 없음"

  # 비율 지표 포맷팅
  for label, key, format_type in ratio_metrics:
    if key in financial_data and financial_data[key] is not None:
      value = financial_data[key]
      if format_type == '.2f':
        formatted_text += f"\n- {label}: {value:.2f}%"
      else:
        formatted_text += f"\n- {label}: {value}"
    elif key in financial_data:
      formatted_text += f"\n- {label}: 데이터 없음"

  # 파생 변수 포맷팅
  for label, key, format_type in derived_metrics:
    if key in financial_data and financial_data[key] is not None:
      value = financial_data[key]
      if format_type == ',':
        formatted_text += f"\n- {label}: {value:,.0f}"
      elif format_type == '.2f':
        formatted_text += f"\n- {label}: {value:.2f}"
      else:
        formatted_text += f"\n- {label}: {value}"
    elif key in financial_data:
      formatted_text += f"\n- {label}: 데이터 없음"

  # 기타 재무 데이터 추가 (위에 명시되지 않은 키)
  for key, value in financial_data.items():
    if key not in [item[1] for item in basic_metrics + ratio_metrics + derived_metrics]:
      if value is None:
        formatted_text += f"\n- {key}: 데이터 없음"
      elif isinstance(value, (int, float)):
        if abs(value) > 1000:
          formatted_text += f"\n- {key}: {value:,.0f}"
        else:
          formatted_text += f"\n- {key}: {value:.2f}"
      else:
        formatted_text += f"\n- {key}: {value}"

  return formatted_text
