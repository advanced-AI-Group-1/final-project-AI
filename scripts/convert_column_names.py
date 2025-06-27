import pandas as pd
import os

# 한글-영어 컬럼명 매핑
column_mapping = {
    '매출액': 'revenue',
    '영업이익': 'operating_profit',
    '당기순이익': 'net_income',
    '총자산': 'total_assets',
    '총부채': 'total_liabilities',
    '자본총계': 'total_equity',
    '자본금': 'capital',
    '영업활동현금흐름': 'operating_cash_flow',
    '이자발생부채': 'interest_bearing_debt',
    '부채비율': 'debt_ratio',
    'ROA': 'ROA',
    'ROE': 'ROE',
    '매출총자산회전율': 'asset_turnover_ratio',
    '이자총자산비율': 'interest_to_assets_ratio',
    '이자매출비율': 'interest_to_revenue_ratio',
    '현금흐름대비이자': 'cash_flow_to_interest',
    '이자대비현금흐름': 'interest_to_cash_flow',
    '로그총자산': 'log_total_assets',
    '로그총부채': 'log_total_liabilities'
}

# CSV 파일 경로
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
input_file = os.path.join(base_dir, 'data', 'csv', 'dart_general_company_financial_fixed.csv')
output_file = os.path.join(base_dir, 'data', 'csv', 'dart_general_company_financial_fixed_en.csv')

# CSV 파일 읽기
print(f"Reading CSV file: {input_file}")
df = pd.read_csv(input_file)

# 컬럼명 변경
print("Converting column names from Korean to English")
df = df.rename(columns=column_mapping)

# 변경된 CSV 파일 저장
print(f"Saving CSV file with English column names: {output_file}")
df.to_csv(output_file, index=False)

print("Column conversion completed successfully!")
print("Original columns:", list(column_mapping.keys()))
print("New columns:", list(column_mapping.values()))
