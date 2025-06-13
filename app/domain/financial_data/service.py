from typing import List, Dict, Any
from app.infrastructure.vector_store.repository import VectorStoreRepository
from app.infrastructure.models.financial_data import FinancialDataModel

class FinancialDataService:
    """
    재무제표 데이터를 검색하고 처리하는 서비스 클래스
    """
    def __init__(self):
        self.vector_store = VectorStoreRepository()
        
    async def search_similar_financial_data(self, prompt: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        프롬프트와 유사도가 높은 기업의 재무제표 데이터를 검색합니다.
        
        Args:
            prompt (str): 사용자 프롬프트
            top_k (int): 반환할 상위 결과 수
            
        Returns:
            List[Dict[str, Any]]: 유사도 높은 기업의 재무제표 데이터 목록
        """
        # 벡터 저장소에서 유사한 문서 검색
        similar_docs = await self.vector_store.search_similar_documents(prompt, top_k)
        
        results = []
        for doc in similar_docs:
            # 문서 ID를 기반으로 실제 재무제표 데이터 조회
            company_data = await FinancialDataModel.get_financial_data_by_id(doc.document_id)
            
            result = {
                "company_name": company_data.company_name,
                "similarity_score": doc.similarity,
                "financial_statements": company_data.financial_statements
            }
            results.append(result)
            
        return results
