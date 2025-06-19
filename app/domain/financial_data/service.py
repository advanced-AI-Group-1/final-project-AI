from typing import List, Dict, Any
from app.infrastructure.vector_store.repository import VectorStoreRepository
import os
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinancialDataService:
  """
    재무제표 데이터를 검색하고 처리하는 서비스 클래스
    """

  def __init__(self):
    self.vector_store = VectorStoreRepository()

  def initialize_vector_store(self):
    """
        벡터 스토어를 초기화하고 데이터를 로드합니다.
        """
    try:
      logger.info("벡터 스토어 초기화 시작")
      csv_path = os.path.join("data", "csv", "dart_general_company_financial_fixed.csv")
      logger.info(f"CSV 파일 경로: {csv_path}")

      if not os.path.exists(csv_path):
        logger.error(f"CSV 파일이 존재하지 않습니다: {csv_path}")
        return False

      logger.info("벡터 스토어 구축 시작")
      self.vector_store.build_vector_store(csv_path=csv_path,
                                           collection_name="korean_financial_data",
                                           embedding_model="voyage-3")
      logger.info("벡터 스토어 구축 완료")
      return True
    except Exception as e:
      logger.error(f"벡터 스토어 초기화 중 오류 발생: {str(e)}")
      return False

  async def search_similar_financial_data(self, prompt: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
        프롬프트와 유사도가 높은 기업의 재무제표 데이터를 검색합니다.

        Args:
            prompt (str): 사용자 프롬프트
            top_k (int): 반환할 상위 결과 수

        Returns:
            List[Dict[str, Any]]: 유사도 높은 기업의 재무제표 데이터 목록
        """
    # 벡터 저장소에서 유사한 회사 검색
    search_results = await self.vector_store.search_similar_companies(query=prompt,
                                                                      n_results=top_k,
                                                                      embedding_model="voyage-3")

    # 결과 형식 변환
    results = []
    for company in search_results["results"]:
      # 재무 데이터 추출
      financial_data = {}
      for key, value in company["metadata"].items():
        if key in ['매출액', '영업이익', '당기순이익', '총자산', '총부채', '자본총계', 'ROA', 'ROE', '부채비율', '매출총자산회전율']:
          financial_data[key] = value

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

  async def filter_financial_data(self,
                                  industry: str = None,
                                  min_revenue: float = None,
                                  max_debt_ratio: float = None,
                                  top_k: int = 5) -> List[Dict[str, Any]]:
    """
        특정 조건에 맞는 기업의 재무제표 데이터를 필터링합니다.

        Args:
            industry (str): 업종
            min_revenue (float): 최소 매출액
            max_debt_ratio (float): 최대 부채비율
            top_k (int): 반환할 상위 결과 수

        Returns:
            List[Dict[str, Any]]: 조건에 맞는 기업의 재무제표 데이터 목록
        """
    # 벡터 저장소에서 필터링 검색
    filter_results = await self.vector_store.filter_search(industry=industry,
                                                           min_revenue=min_revenue,
                                                           max_debt_ratio=max_debt_ratio,
                                                           n_results=top_k)

    # 결과 형식 변환
    results = []
    for company in filter_results["results"]:
      # 재무 데이터 추출
      financial_data = {}
      for key, value in company["metadata"].items():
        if key in ['매출액', '영업이익', '당기순이익', '총자산', '총부채', '자본총계', 'ROA', 'ROE', '부채비율', '매출총자산회전율']:
          financial_data[key] = value

      result = {
          "company_name": company["corp_name"],
          "similarity_score": 1.0,  # 필터링 검색에서는 유사도가 없으므로 1.0으로 설정
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
