from typing import List, Dict, Any
import os
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.schema import Document

class VectorStoreRepository:
    """
    재무제표 데이터의 벡터 저장소 관리를 위한 리포지토리 클래스
    """
    def __init__(self):
        # 환경 변수에서 OpenAI API 키 가져오기
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        # 임베딩 모델 초기화
        self.embeddings = OpenAIEmbeddings(api_key=self.api_key)
        
        # 벡터 저장소 경로
        self.persist_directory = "data/vector_store"
        
        # 벡터 저장소 초기화 또는 로드
        self._initialize_vector_store()
        
    def _initialize_vector_store(self):
        """
        벡터 저장소 초기화 또는 기존 저장소 로드
        """
        # 저장 디렉토리가 없으면 생성
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # 벡터 저장소 로드 또는 생성
        try:
            self.vector_store = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
        except Exception as e:
            print(f"벡터 저장소 초기화 중 오류 발생: {str(e)}")
            # 오류 발생 시 새로운 벡터 저장소 생성
            self.vector_store = Chroma(
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )
    
    async def add_documents(self, documents: List[Dict[str, Any]]):
        """
        문서를 벡터 저장소에 추가합니다.
        
        Args:
            documents (List[Dict[str, Any]]): 추가할 문서 목록
        """
        # 문서 형식 변환
        langchain_docs = []
        for doc in documents:
            # 문서 내용과 메타데이터 분리
            content = doc.get("content", "")
            metadata = {k: v for k, v in doc.items() if k != "content"}
            
            langchain_docs.append(Document(page_content=content, metadata=metadata))
        
        # 벡터 저장소에 문서 추가
        self.vector_store.add_documents(langchain_docs)
        
        # 변경사항 저장
        self.vector_store.persist()
        
    async def search_similar_documents(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        쿼리와 유사한 문서를 검색합니다.
        
        Args:
            query (str): 검색 쿼리
            top_k (int): 반환할 상위 결과 수
            
        Returns:
            List[Dict[str, Any]]: 유사도 높은 문서 목록
        """
        # 유사 문서 검색
        docs_with_scores = self.vector_store.similarity_search_with_score(query, k=top_k)
        
        results = []
        for doc, score in docs_with_scores:
            # 유사도 점수 변환 (거리를 유사도로 변환)
            similarity = 1.0 / (1.0 + score)
            
            result = {
                "document_id": doc.metadata.get("document_id", ""),
                "company_name": doc.metadata.get("company_name", ""),
                "content": doc.page_content,
                "similarity": similarity,
                "metadata": doc.metadata
            }
            results.append(result)
            
        return results
