"""
보고서 생성에 필요한 프롬프트 템플릿을 제공하는 모듈
"""

# 요약 카드 프롬프트 템플릿
SUMMARY_CARD_PROMPT = """
기업명: {company_name}
업종: {industry_name}
시장구분: {market_type}

다음 재무 데이터와 신용등급 정보를 바탕으로 **1페이지 요약 카드형 보고서**를 작성해주세요:

재무 데이터:
{financial_data}

신용등급 정보:
{credit_rating}

다음 형식으로 작성해주세요:

## 📘 신용분석 요약 카드

**기업명**: {company_name}
**평가일자**: {evaluation_date}
**신용등급**: [등급] (예: AA+)

**현재 등급 요약** (100자 이내):
[등급의 핵심 의미와 배경]

**주요 강점 키워드** (3개 이내):
[키워드1], [키워드2], [키워드3]

**주요 약점 키워드** (3개 이내):
[키워드1], [키워드2], [키워드3]

**핵심 재무지표**:
- ROA: [수치]% ([평가])
- ROE: [수치]% ([평가])
- 부채비율: [수치]% ([평가])
- 영업이익률: [수치]% ([평가])

**신용등급 변동 가능성**:
[상향/유지/하향] 가능성이 높으며, 그 이유는 [간략한 이유]입니다.
"""

# 재무분석 섹션 프롬프트 템플릿
FINANCIAL_ANALYSIS_PROMPT = """
기업명: {company_name}
업종: {industry_name}
시장구분: {market_type}

다음 재무 데이터를 바탕으로 재무분석 섹션을 작성해주세요:

재무 데이터:
{financial_data}

추가 계산된 재무비율:
{additional_ratios}

다음 항목들을 포함하여 분석해주세요:
1. 수익성 분석 (ROA, ROE, 영업이익률 등)
2. 안정성 분석 (부채비율, 이자보상배율 등)
3. 유동성 분석 (유동비율, 현금흐름 등)
4. 효율성 분석 (자산회전율 등)

각 항목별로 수치와 함께 해당 수치가 의미하는 바를 설명해주세요.
"""

# 신용등급 평가 섹션 프롬프트 템플릿
CREDIT_RATING_ANALYSIS_PROMPT = """
기업명: {company_name}
업종: {industry_name}
시장구분: {market_type}

다음 재무 데이터와 신용등급 정보를 바탕으로 신용등급 평가 섹션을 작성해주세요:

재무 데이터:
{financial_data}

신용등급 정보:
{credit_rating}

다음 항목들을 포함하여 분석해주세요:
1. 현재 신용등급의 의미와 산출 근거
2. 주요 신용 강점 요인
3. 주요 신용 약점 요인
4. 향후 신용등급 변동 가능성 및 요인

신용등급 평가는 재무적 요소와 비재무적 요소를 모두 고려하여 설명해주세요.
"""

# 결론 및 제언 섹션 프롬프트 템플릿
CONCLUSION_PROMPT = """
기업명: {company_name}
업종: {industry_name}
시장구분: {market_type}

다음 재무 데이터와 신용등급 정보를 바탕으로 결론 및 제언 섹션을 작성해주세요:

재무 데이터:
{financial_data}

신용등급 정보:
{credit_rating}

다음 항목들을 포함하여 작성해주세요:
1. 종합 평가 요약
2. 기업의 주요 재무적 과제
3. 신용등급 개선을 위한 제언
4. 향후 모니터링이 필요한 핵심 지표

제언은 구체적이고 실행 가능한 내용으로 작성해주세요.
"""

# 섹션 정의
DEFAULT_SECTIONS = [{
    "name": "요약",
    "description": "기업 신용평가 결과의 핵심 요약",
    "requires_calculation": False,
    "requires_research": False,
    "char_limit": 500
}, {
    "name": "기업 개요",
    "description": "기업의 기본 정보 및 사업 개요",
    "requires_calculation": False,
    "requires_research": False,
    "char_limit": 300
}, {
    "name": "재무 분석",
    "description": "손익계산서, 재무상태표, 현금흐름표 분석",
    "requires_calculation": True,
    "requires_research": False,
    "char_limit": 800
}, {
    "name": "신용등급 평가",
    "description": "신용등급 산출 근거 및 평가",
    "requires_calculation": False,
    "requires_research": False,
    "char_limit": 500
}, {
    "name": "위험 요소",
    "description": "주요 재무적, 비재무적 위험 요소",
    "requires_calculation": False,
    "requires_research": False,
    "char_limit": 400
}, {
    "name": "결론 및 제언",
    "description": "종합 평가 및 개선 방향 제시",
    "requires_calculation": False,
    "requires_research": False,
    "char_limit": 400
}]
