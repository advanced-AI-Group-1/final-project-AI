#region legacy code

# from typing import List, Dict, Any
# from app.infrastructure.vector_store.repository import VectorStoreRepository
# import os
# import logging

# # 로깅 설정
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)


# class FinancialDataService:
#   """
#     재무제표 데이터를 검색하고 처리하는 서비스 클래스
#     """

#   def __init__(self):
#     self.vector_store = VectorStoreRepository()

#   def initialize_vector_store(self):
#     """
#         벡터 스토어를 초기화하고 데이터를 로드합니다.
#         """
#     try:
#       logger.info("벡터 스토어 초기화 시작")
#       # 영어 컬럼명을 사용하는 CSV 파일 경로로 변경
#       csv_path = os.path.join("data", "csv", "dart_general_company_financial_fixed_en.csv")
#       logger.info(f"CSV 파일 경로: {csv_path}")

#       if not os.path.exists(csv_path):
#         logger.error(f"CSV 파일이 존재하지 않습니다: {csv_path}")
#         return False

#       logger.info("벡터 스토어 구축 시작")
#       self.vector_store.build_vector_store(csv_path=csv_path,
#                                            collection_name="korean_financial_data",
#                                            embedding_model="voyage-finance-2")
#       logger.info("벡터 스토어 구축 완료")
#       return True
#     except Exception as e:
#       logger.error(f"벡터 스토어 초기화 중 오류 발생: {str(e)}")
#       return False

#   async def search_similar_financial_data(self, prompt: str, top_k: int = 8) -> List[Dict[str, Any]]:
#     """
#         프롬프트와 유사도가 높은 기업의 재무제표 데이터를 검색합니다.

#         Args:
#             prompt (str): 사용자 프롬프트
#             top_k (int): 반환할 상위 결과 수

#         Returns:
#             List[Dict[str, Any]]: 유사도 높은 기업의 재무제표 데이터 목록
#         """
#     # 벡터 저장소에서 유사한 회사 검색
#     search_results = await self.vector_store.search_similar_companies(query=prompt,
#                                                                       n_results=top_k,
#                                                                       embedding_model="voyage-finance-2")

#     # 결과 형식 변환
#     results = []
#     for company in search_results["results"]:
#       # 재무 데이터 추출 - 모든 메타데이터 포함
#       financial_data = {}
#       for key, value in company["metadata"].items():
#         # 모든 재무 데이터 및 파생변수 포함 (필터링 제거)
#         financial_data[key] = value

#       result = {
#           "company_name": company["corp_name"],
#           "similarity_score": company["similarity"],
#           "financial_statements": {
#               "corp_code": company["corp_code"],
#               "corp_name": company["corp_name"],
#               "market_type": company["market_type"],
#               "industry_name": company["industry_name"],
#               "financial_data": financial_data
#           }
#       }
#       results.append(result)

#     return results

#   async def filter_financial_data(self,
#                                   industry: str = None,
#                                   min_revenue: float = None,
#                                   max_debt_ratio: float = None,
#                                   top_k: int = 8) -> List[Dict[str, Any]]:
#     """
#         특정 조건에 맞는 기업의 재무제표 데이터를 필터링합니다.

#         Args:
#             industry (str): 업종
#             min_revenue (float): 최소 매출액
#             max_debt_ratio (float): 최대 부채비율
#             top_k (int): 반환할 상위 결과 수

#         Returns:
#             List[Dict[str, Any]]: 조건에 맞는 기업의 재무제표 데이터 목록
#         """
#     # 벡터 저장소에서 필터링 검색
#     filter_results = await self.vector_store.filter_search(industry=industry,
#                                                            min_revenue=min_revenue,
#                                                            max_debt_ratio=max_debt_ratio,
#                                                            n_results=top_k)

#     # 결과 형식 변환
#     results = []
#     for company in filter_results["results"]:
#       # 재무 데이터 추출 - 모든 메타데이터 포함
#       financial_data = {}
#       for key, value in company["metadata"].items():
#         # 모든 재무 데이터 및 파생변수 포함 (필터링 제거)
#         financial_data[key] = value

#       result = {
#           "company_name": company["corp_name"],
#           "similarity_score": 1.0,  # 필터링 검색에서는 유사도가 없으므로 1.0으로 설정
#           "financial_statements": {
#               "corp_code": company["corp_code"],
#               "corp_name": company["corp_name"],
#               "market_type": company["market_type"],
#               "industry_name": company["industry_name"],
#               "financial_data": financial_data
#           }
#       }
#       results.append(result)

#     return results

#endregion

from typing import List, Dict, Any, Optional
from app.infrastructure.vector_store.repository import VectorStoreRepository
import logging
import re

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinancialDataService:
    """
    재무제표 데이터를 검색하고 처리하는 서비스 클래스
    """

    def __init__(self):
        self.vector_store = VectorStoreRepository()

    def initialize_vector_store(self, csv_path: Optional[str] = None) -> bool:
        """
        CSV 파일 데이터로 벡터 스토어를 초기화합니다.
        
        Args:
            csv_path: CSV 파일 경로 (기본값: data/csv/dart_general_company_financial_fixed_en.csv)
            
        Returns:
            bool: 초기화 성공 여부
        """
        import os
        
        try:
            # 기본 CSV 파일 경로 설정
            if csv_path is None:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                csv_path = os.path.join(base_dir, 'data', 'csv', 'dart_general_company_financial_fixed_en.csv')
            
            logger.info(f"벡터 스토어 초기화 시작 - CSV 파일: {csv_path}")
            
            # 벡터 스토어 초기화
            success = self.vector_store.initialize_vector_store(csv_path=csv_path)
            
            if success:
                logger.info("벡터 스토어 초기화 완료")
            else:
                logger.error("벡터 스토어 초기화 실패")
                
            return success
            
        except Exception as e:
            logger.error(f"벡터 스토어 초기화 중 오류 발생: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def search_similar_financial_data(self, prompt: str, top_k: int = 8) -> List[Dict[str, Any]]:
        """
        프롬프트와 유사한 기업 검색
        """
        search_results = await self.vector_store.search_similar_companies(
            query=prompt,
            n_results=top_k,
            embedding_model="voyage-finance-2"
        )

        results = []
        for company in search_results["results"]:
            financial_data = {key: value for key, value in company["metadata"].items()}
            result = {
                "company_name": company["corp_name"],
                "similarity_score": company["similarity"],
                "financial_statements": {
                    "corp_code": company["corp_code"],
                    "corp_name": company["corp_name"],
                    "market_type": company["market_type"],
                    "industry_name": company["industry_name"],
                    "financial_data": financial_data
                }
            }
            results.append(result)

        return results

    async def filter_financial_data(
        self,
        industry: Optional[str] = None,
        raw_conditions: Optional[Dict[str, Dict[str, float]]] = None,
        top_k: int = 8
    ) -> List[Dict[str, Any]]:
        """
        조건 기반 필터링
        """
        column_name_mapping = {
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

        conditions_dict = {}
        if raw_conditions:
            for kor_key, cond in raw_conditions.items():
                eng_key = column_name_mapping.get(kor_key)
                if not eng_key:
                    continue
                if 'min' in cond:
                    conditions_dict[f'min_{eng_key}'] = cond['min']
                if 'max' in cond:
                    conditions_dict[f'max_{eng_key}'] = cond['max']

        logger.info(f"[필터 조건] industry: {industry}")
        logger.info(f"[조건 딕셔너리] {conditions_dict}")

        filter_results = await self.vector_store.filter_search(
            industry=industry,
            conditions_dict=conditions_dict,
            n_results=top_k
        )

        results = []
        for company in filter_results["results"]:
            financial_data = {key: value for key, value in company["metadata"].items()}
            result = {
                "company_name": company["corp_name"],
                "similarity_score": 1.0,
                "financial_statements": {
                    "corp_code": company["corp_code"],
                    "corp_name": company["corp_name"],
                    "market_type": company["market_type"],
                    "industry_name": company["industry_name"],
                    "financial_data": financial_data
                }
            }
            results.append(result)

        return results

    def extract_conditions_from_prompt(self, prompt: str) -> Dict[str, float]:
        """
        사용자 프롬프트에서 조건 추출 (예: 매출 5조 이상 → {'min_revenue': 5e12})
        """
        unit_map = {"만": 1e4, "억": 1e8, "조": 1e12, "%": 1}
        key_map = {
            "매출": "revenue",
            "매출액": "revenue",
            "영업이익": "operating_profit",
            "당기순이익": "net_income",
            "부채비율": "debt_ratio",
            "ROE": "ROE",
            "ROA": "ROA",
            "자본금": "capital"
        }

        conditions = {}
        pattern = r"(매출액|매출|영업이익|당기순이익|부채비율|ROE|ROA|자본금)[은이]?\s*(\d+\.?\d*)\s*([만억조%]?)\s*(이상|초과|이하|미만|보다 작은|보다 큰)?"
        matches = re.findall(pattern, prompt)

        for kor_key, num, unit, comp in matches:
            eng_key = key_map.get(kor_key)
            if not eng_key:
                continue
            multiplier = unit_map.get(unit, 1)
            value = float(num) * multiplier / 1e9

             # ✅ 이거 추가
            logger.info(f"[조건 해석] {kor_key} → {eng_key}, 수치: {num}{unit} → 환산값: {value} (billion KRW)")


            if comp in ["이상", "초과", "보다 큰"]:
                conditions[f"min_{eng_key}"] = value
            elif comp in ["이하", "미만", "보다 작은"]:
                conditions[f"max_{eng_key}"] = value
            else:
                conditions[f"min_{eng_key}"] = value  # 기본적으로 이상으로 처리

        return conditions

    def convert_extracted_conditions(self, extracted: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        """
        'min_revenue': 100000 → {'revenue': {'min': 100000}} 형식으로 변환
        """
        converted = {}
        for key, value in extracted.items():
            if key.startswith("min_"):
                col = key[4:]
                converted[col] = {"min": value}
            elif key.startswith("max_"):
                col = key[4:]
                converted[col] = {"max": value}
        return converted

    async def filter_financial_data_from_prompt(self, prompt: str, industry: Optional[str] = None, top_k: int = 8):
        """
        자연어로부터 조건 추출 + 유사도 + 필터링 통합
        """
        logger.info(f"[자연어 쿼리] {prompt}")
        extracted = self.extract_conditions_from_prompt(prompt)
        logger.info(f"[추출된 조건] {extracted}")
        converted = self.convert_extracted_conditions(extracted)
        logger.info(f"[변환된 딕셔너리] {converted}")

        return await self.vector_store.search_similar_companies_with_filter(
            query=prompt,
            industry=industry,
            conditions_dict=converted,
            n_results=top_k
        )
