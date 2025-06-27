# 레거시 Chroma 코드는 legacy_chroma_repository.py 파일로 이동되었습니다.
# 현재 프로젝트는 Qdrant를 사용합니다.

import logging
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue, Range
from voyageai import Client as VoyageClient
from dotenv import load_dotenv

from app.core.config import settings

# 로깅 설정
logger = logging.getLogger(__name__)


# 사용자 조건에 따라 Qdrant 필터 객체 생성
def build_filter_from_user_query(industry: Optional[str] = None,
                                 conditions_dict: Optional[dict] = None) -> Optional[Filter]:
    conditions = []

    if industry:
        conditions.append(FieldCondition(
            key="industry_name", match=MatchValue(value=industry)
        ))

    if conditions_dict:
        for key, value in conditions_dict.items():
            if value is None:
                continue

            if key.startswith("min_"):
                field = key.replace("min_", "")
                conditions.append(FieldCondition(
                    key=field,
                    range=Range(gte=value)
                ))
            elif key.startswith("max_"):
                field = key.replace("max_", "")
                conditions.append(FieldCondition(
                    key=field,
                    range=Range(lte=value)
                ))

    return Filter(must=conditions) if conditions else None


# Qdrant + Voyage 기반 벡터 검색 리포지토리
class VectorStoreRepository:
    def __init__(self):
        self.qdrant = QdrantClient(
            url=settings.VECTOR_STORE_PATH,
            api_key=settings.QDRANT_API_KEY,
            prefer_grpc=False
        )
        self.voyage = VoyageClient(api_key=settings.VOYAGE_API_KEY)
        self.collection_name = "financial_data"
        
    # CSV 데이터로 벡터 스토어 초기화
    def initialize_vector_store(self, csv_path: str) -> bool:
        """
        CSV 파일에서 데이터를 읽어 Qdrant 벡터 스토어를 초기화합니다.
        
        Args:
            csv_path: CSV 파일 경로
            
        Returns:
            bool: 초기화 성공 여부
        """
        import pandas as pd
        import numpy as np
        import os
        
        try:
            logger.info(f"벡터 스토어 초기화 시작 - CSV 파일: {csv_path}")
            
            # CSV 파일 존재 확인
            if not os.path.exists(csv_path):
                logger.error(f"CSV 파일이 존재하지 않습니다: {csv_path}")
                return False
                
            # CSV 파일 읽기
            logger.info("CSV 파일 읽는 중...")
            df = pd.read_csv(csv_path)
            logger.info(f"CSV 데이터 로드 완료: {len(df)}개 행")
            
            # 필수 컬럼 확인
            required_columns = ['corp_code', 'corp_name', 'market_type', 'industry_name']
            for col in required_columns:
                if col not in df.columns:
                    logger.error(f"필수 컬럼이 없습니다: {col}")
                    return False
            
            # 기존 컬렉션 삭제 (있는 경우)
            try:
                logger.info(f"기존 컬렉션 삭제 시도: {self.collection_name}")
                self.qdrant.delete_collection(collection_name=self.collection_name)
                logger.info("기존 컬렉션 삭제 완료")
            except Exception as e:
                logger.info(f"컬렉션 삭제 중 예외 발생 (무시 가능): {str(e)}")
            
            # 새 컬렉션 생성
            logger.info(f"새 컬렉션 생성: {self.collection_name}")
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config={"size": 1024, "distance": "Cosine"}
            )
            
            # 데이터 준비 및 임베딩 생성
            logger.info("데이터 임베딩 생성 중...")
            batch_size = 100  # Voyage API 제한 고려
            
            # 회사 설명 텍스트 생성
            df['description'] = df.apply(
                lambda row: f"{row['corp_name']} - {row['industry_name']} - {row['market_type']}", 
                axis=1
            )
            
            # 배치 처리
            for i in range(0, len(df), batch_size):
                batch_df = df.iloc[i:i+batch_size]
                logger.info(f"배치 처리 중: {i} ~ {i+len(batch_df)-1}")
                
                # 임베딩 생성
                texts = batch_df['description'].tolist()
                embeddings = self.voyage.embed(
                    texts=texts,
                    model="voyage-finance-2",
                    input_type="document"
                ).embeddings
                
                # 페이로드 생성
                points = []
                for j, row in enumerate(batch_df.itertuples()):
                    # 모든 컬럼을 페이로드에 추가
                    payload = {col: getattr(row, col) for col in df.columns if col != 'Index'}
                    
                    # NaN 값 처리
                    for k, v in payload.items():
                        if pd.isna(v):
                            payload[k] = None
                        elif isinstance(v, np.integer):
                            payload[k] = int(v)
                        elif isinstance(v, np.floating):
                            payload[k] = float(v)
                    
                    points.append({
                        "id": i+j,  # 문자열 대신 정수형 ID 사용
                        "vector": embeddings[j],
                        "payload": payload
                    })
                
                # Qdrant에 포인트 추가
                self.qdrant.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                
                logger.info(f"배치 {i//batch_size + 1} 처리 완료: {len(points)}개 포인트 추가")
            
            logger.info(f"벡터 스토어 초기화 완료: 총 {len(df)}개 데이터 추가됨")
            return True
            
        except Exception as e:
            logger.error(f"벡터 스토어 초기화 중 오류 발생: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    # 유사도 기반 검색
    async def search_similar_companies(self, query: str, n_results: int = 8, embedding_model: str = "voyage-finance-2"):
        logger.info(f"쿼리: {query} → 유사 기업 검색 중...")

        query_embedding = self.voyage.embed(
            texts=[query],
            model=embedding_model,
            input_type="query"
        ).embeddings[0]

        result = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=n_results,
            with_payload=True
        )

        return {
            "query": query,
            "results": [
                {
                    "corp_code": r.payload.get("corp_code"),
                    "corp_name": r.payload.get("corp_name"),
                    "market_type": r.payload.get("market_type"),
                    "industry_name": r.payload.get("industry_name"),
                    "similarity": r.score,
                    "metadata": r.payload
                } for r in result
            ]
        }

    # 조건 기반 필터 검색
    async def filter_search(
        self,
        industry: Optional[str] = None,
        conditions_dict: Optional[dict] = None,
        n_results: int = 8
    ):
        logger.info("필터 기반 검색 시작")
        

        q_filter = build_filter_from_user_query(industry, conditions_dict)
        dummy_vector = [0.0] * 1024  # 임시 쿼리 벡터

        logger.info(f"[Qdrant 필터 객체] {q_filter}")

        result = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=dummy_vector,
            query_filter=q_filter,
            limit=n_results,
            with_payload=True
        )

        return {
            "filter_criteria": {
                "industry": industry,
                "conditions": conditions_dict
            },
            "results": [
                {
                    "corp_code": r.payload.get("corp_code"),
                    "corp_name": r.payload.get("corp_name"),
                    "market_type": r.payload.get("market_type"),
                    "industry_name": r.payload.get("industry_name"),
                    "similarity": r.score,
                    "metadata": r.payload
                } for r in result
            ]
        }

    # 유사도 + 필터 조합 검색
    async def search_similar_companies_with_filter(
        self,
        query: str,
        industry: Optional[str] = None,
        conditions_dict: Optional[dict] = None,
        n_results: int = 8,
        embedding_model: str = "voyage-finance-2"
    ):
        logger.info(f"쿼리: {query} → 유사도 + 필터 검색 시작")

        query_embedding = self.voyage.embed(
            texts=[query],
            model=embedding_model,
            input_type="query"
        ).embeddings[0]

        q_filter = build_filter_from_user_query(industry, conditions_dict)

        result = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=q_filter,
            limit=n_results,
            with_payload=True
        )

        return {
            "query": query,
            "filter_criteria": {
                "industry": industry,
                "conditions": conditions_dict
            },
            "results": [
                {
                    "corp_code": r.payload.get("corp_code"),
                    "corp_name": r.payload.get("corp_name"),
                    "market_type": r.payload.get("market_type"),
                    "industry_name": r.payload.get("industry_name"),
                    "similarity": r.score,
                    "metadata": r.payload
                } for r in result
            ]
        }
