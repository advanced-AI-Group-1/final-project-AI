#region legacy code

# import logging
# import os
# from typing import List, Dict, Optional

# import chromadb
# import pandas as pd
# import voyageai
# from dotenv import load_dotenv

# # 로깅 설정
# logger = logging.getLogger(__name__)


# class VectorStoreRepository:
#   """
#       재무제표 데이터의 벡터 저장소 관리를 위한 리포지토리 클래스
#       VoyageAI와 ChromaDB를 사용하여 구현
#       """

#   def __init__(self, api_key=None):
#     # .env 파일 로드
#     load_dotenv()
#     # 환경 변수에서 VoyageAI API 키 가져오기 또는 매개변수로 전달된 키 사용
#     self.api_key = api_key or os.getenv("VOYAGE_API_KEY")

#     # API 키 로깅 (마스킹 처리)
#     if self.api_key:
#       masked_key = self.api_key[:4] + "*" * (len(self.api_key) - 8) + self.api_key[-4:] if len(
#           self.api_key) > 8 else "****"
#       logger.info(f"VoyageAI API 키 로드됨: {masked_key}")
#     else:
#       logger.error("VoyageAI API 키를 찾을 수 없습니다!")

#     # VoyageAI 클라이언트 초기화 및 전역 API 키 설정
#     voyageai.api_key = self.api_key  # 전역 API 키 설정 추가
#     self.voyage_client = voyageai.Client(api_key=self.api_key)

#     # ChromaDB 클라이언트 초기화
#     self.persist_directory = "data/vector_store"
#     os.makedirs(self.persist_directory, exist_ok=True)
#     self.chroma_client = chromadb.PersistentClient(path=self.persist_directory)

#     # 기본 컬렉션 이름
#     self.collection_name = "korean_financial_data"

#     # 컬렉션 초기화 또는 로드
#     self._initialize_collection()

#   def _initialize_collection(self):
#     """
#             ChromaDB 컬렉션 초기화 또는 기존 컬렉션 로드
#             """
#     try:
#       logger.info(f"컬렉션 '{self.collection_name}'을 로드하려고 시도합니다.")
#       self.collection = self.chroma_client.get_collection(name=self.collection_name)
#       logger.info(f"컬렉션 '{self.collection_name}'을 성공적으로 로드했습니다.")
#     except Exception as e:
#       logger.error(f"컬렉션 '{self.collection_name}' 로드 중 오류 발생: {str(e)}")
#       logger.info(f"새 컬렉션 '{self.collection_name}'을 생성합니다.")
#       self.collection = self.chroma_client.create_collection(
#           name=self.collection_name, metadata={"description": "Korean financial data with embeddings"})
#       logger.info(f"새 컬렉션 '{self.collection_name}'이 성공적으로 생성되었습니다.")

#   def create_text_representation(self, row: pd.Series) -> str:
#     """
#             각 행의 데이터를 자연어 텍스트로 변환
            
#             Args:
#                 row (pd.Series): 재무 데이터 행
                
#             Returns:
#                 str: 텍스트 표현
#             """
#     text_parts = []

#     # 기본 회사 정보
#     text_parts.append(f"회사명: {row['corp_name']}")
#     text_parts.append(f"시장구분: {row['market_type']}")
#     text_parts.append(f"업종: {row['industry_name']}")

#     # 재무 정보 (억원 단위로 표현)
#     if pd.notna(row['revenue']):
#       text_parts.append(f"매출액: {row['revenue'] / 100000000:.1f}억원")
#     if pd.notna(row['operating_profit']):
#       text_parts.append(f"영업이익: {row['operating_profit'] / 100000000:.1f}억원")
#     if pd.notna(row['net_income']):
#       text_parts.append(f"당기순이익: {row['net_income'] / 100000000:.1f}억원")
#     if pd.notna(row['total_assets']):
#       text_parts.append(f"총자산: {row['total_assets'] / 100000000:.1f}억원")
#     if pd.notna(row['total_liabilities']):
#       text_parts.append(f"총부채: {row['total_liabilities'] / 100000000:.1f}억원")
#     if pd.notna(row['total_equity']):
#       text_parts.append(f"자본총계: {row['total_equity'] / 100000000:.1f}억원")

#     # 재무 비율
#     if pd.notna(row['debt_ratio']):
#       text_parts.append(f"부채비율: {row['debt_ratio']:.2f}%")
#     if pd.notna(row['ROA']):
#       text_parts.append(f"ROA: {row['ROA']:.2f}%")
#     if pd.notna(row['ROE']):
#       text_parts.append(f"ROE: {row['ROE']:.2f}%")
#     if pd.notna(row['asset_turnover_ratio']):
#       text_parts.append(f"매출총자산회전율: {row['asset_turnover_ratio']:.2f}")

#     return " | ".join(text_parts)

#   def embed_with_voyage(self, texts: List[str], model: str = "voyage-3") -> List[List[float]]:
#     """
#             Voyage AI를 사용하여 텍스트 임베딩
            
#             Args:
#                 texts (List[str]): 임베딩할 텍스트 목록
#                 model (str): 사용할 임베딩 모델
                
#             Returns:
#                 List[List[float]]: 임베딩 벡터 목록
#             """
#     # 배치 사이즈를 128로 제한 (Voyage API 제한)
#     batch_size = 128
#     all_embeddings = []

#     for i in range(0, len(texts), batch_size):
#       batch = texts[i:i + batch_size]

#       # Voyage Finance 2 사용 시
#       if model == "voyage-finance-2":
#         response = self.voyage_client.embed(
#             texts=batch,
#             model="voyage-finance-2",
#             input_type="document"  # 문서 임베딩용
#         )
#       else:  # voyage-3 사용 시
#         response = self.voyage_client.embed(texts=batch, model="voyage-3", input_type="document")

#       all_embeddings.extend(response.embeddings)

#     return all_embeddings

#   def build_vector_store(self, csv_path: str, collection_name: Optional[str] = None, embedding_model: str = "voyage-3"):
#     """
#             CSV 파일에서 데이터를 로드하여 벡터 스토어 구축
            
#             Args:
#                 csv_path (str): CSV 파일 경로
#                 collection_name (Optional[str]): 컬렉션 이름 (없으면 기본값 사용)
#                 embedding_model (str): 사용할 임베딩 모델
#             """
#     # 컬렉션 이름 설정
#     if collection_name:
#       self.collection_name = collection_name
#       self._initialize_collection()

#     # CSV 파일 로드
#     df = pd.read_csv(csv_path)

#     # 결측값 처리
#     df = df.fillna("")

#     # 기존 컬렉션이 있으면 삭제하고 새로 생성
#     try:
#       self.chroma_client.delete_collection(name=self.collection_name)
#     except:
#       pass

#     self.collection = self.chroma_client.create_collection(
#         name=self.collection_name, metadata={"description": "Korean financial data with embeddings"})

#     # 텍스트 표현 생성
#     logger.info("텍스트 표현 생성 중...")
#     texts = []
#     metadatas = []
#     ids = []

#     for idx, row in df.iterrows():
#       # 텍스트 표현 생성
#       text = self.create_text_representation(row)
#       texts.append(text)

#       # 메타데이터 준비 (검색 시 필터링용)
#       metadata = {
#           "corp_code": str(row['corp_code']),
#           "corp_name": row['corp_name'],
#           "market_type": row['market_type'],
#           "industry_name": row['industry_name'],
#           "is_consolidated": str(row['is_consolidated'])
#       }

#       # 모든 수치 데이터를 메타데이터에 포함
#       for col in df.columns:
#         if col not in ['corp_code', 'corp_name', 'market_type', 'industry_name', 'is_consolidated']:
#           if pd.notna(row[col]) and row[col] != "":
#             try:
#               metadata[col] = float(row[col])
#             except (ValueError, TypeError):
#               # 숫자로 변환할 수 없는 경우 문자열로 저장
#               if pd.notna(row[col]):
#                 metadata[col] = str(row[col])

#       metadatas.append(metadata)
#       ids.append(f"corp_{row['corp_code']}")

#     # 임베딩 생성
#     logger.info(f"{embedding_model}로 임베딩 생성 중...")
#     embeddings = self.embed_with_voyage(texts, model=embedding_model)

#     # ChromaDB에 저장
#     logger.info("ChromaDB에 저장 중...")
#     self.collection.add(embeddings=embeddings, documents=texts, metadatas=metadatas, ids=ids)

#     logger.info(f"총 {len(texts)}개 레코드가 성공적으로 저장되었습니다.")
#     return self.collection

#   async def search_similar_companies(self, query: str, n_results: int = 8, embedding_model: str = "voyage-3"):
#     """
#             쿼리와 유사한 회사 검색
            
#             Args:
#                 query (str): 검색 쿼리
#                 n_results (int): 반환할 결과 수
#                 embedding_model (str): 사용할 임베딩 모델
                
#             Returns:
#                 Dict: 검색 결과
#             """
#     logger.info(f"검색 쿼리: '{query}', 컬렉션 이름: '{self.collection_name}'")

#     # 컬렉션이 제대로 초기화되었는지 확인
#     if not hasattr(self, 'collection') or self.collection is None:
#       logger.error("컬렉션이 초기화되지 않았습니다. _initialize_collection 메서드를 호출합니다.")
#       self._initialize_collection()

#     # 쿼리 임베딩
#     logger.info(f"{embedding_model} 모델을 사용하여 쿼리 임베딩 생성 중...")
#     if embedding_model == "voyage-finance-2":
#       query_embedding = self.voyage_client.embed(
#           texts=[query],
#           model="voyage-finance-2",
#           input_type="query"  # 쿼리 임베딩용
#       ).embeddings[0]
#     else:
#       query_embedding = \
#         self.voyage_client.embed(texts=[query], model="voyage-3", input_type="query").embeddings[0]

#     # 검색 실행
#     logger.info(f"컬렉션 '{self.collection_name}'에서 검색 실행 중...")
#     results = self.collection.query(query_embeddings=[query_embedding],
#                                     n_results=n_results,
#                                     include=["documents", "metadatas", "distances"])

#     # 결과 로깅
#     if results['documents'] and results['documents'][0]:
#       logger.info(f"검색 결과: {len(results['documents'][0])}개 항목 발견")
#     else:
#       logger.warning(f"검색 결과가 비어 있습니다. 컬렉션 '{self.collection_name}'에 데이터가 있는지 확인하세요.")

#     # 결과 형식 변환
#     formatted_results = []
#     for i, (doc, metadata, distance) in enumerate(
#         zip(results['documents'][0] if results['documents'] and results['documents'][0] else [],
#             results['metadatas'][0] if results['metadatas'] and results['metadatas'][0] else [],
#             results['distances'][0] if results['distances'] and results['distances'][0] else [])):
#       similarity = 1 - distance  # 거리를 유사도로 변환
#       formatted_results.append({
#           "rank": i + 1,
#           "corp_name": metadata['corp_name'],
#           "corp_code": metadata['corp_code'],
#           "market_type": metadata['market_type'],
#           "industry_name": metadata['industry_name'],
#           "document": doc,
#           "similarity": similarity,
#           "metadata": metadata
#       })

#     return {"query": query, "results": formatted_results}

#   async def filter_search(self,
#                           industry: str = None,
#                           min_revenue: float = None,
#                           max_debt_ratio: float = None,
#                           n_results: int = 8):
#     """
#             조건부 필터링 검색
            
#             Args:
#                 industry (str): 업종
#                 min_revenue (float): 최소 매출액
#                 max_debt_ratio (float): 최대 부채비율
#                 n_results (int): 반환할 결과 수
                
#             Returns:
#                 Dict: 검색 결과
#             """
#     logger.info(f"필터링 검색 시작, 컬렉션 이름: '{self.collection_name}'")

#     # 컬렉션이 제대로 초기화되었는지 확인
#     if not hasattr(self, 'collection') or self.collection is None:
#       logger.error("컬렉션이 초기화되지 않았습니다. _initialize_collection 메서드를 호출합니다.")
#       self._initialize_collection()

#     # 필터 구성
#     where_clause = {}

#     if industry:
#       where_clause["industry_name"] = industry
#       logger.info(f"업종 필터 적용: {industry}")

#     if min_revenue:
#       where_clause["revenue"] = {"$gte": min_revenue}
#       logger.info(f"최소 매출액 필터 적용: {min_revenue}")

#     if max_debt_ratio:
#       where_clause["debt_ratio"] = {"$lte": max_debt_ratio}
#       logger.info(f"최대 부채비율 필터 적용: {max_debt_ratio}")

#     logger.info(f"필터 조건: {where_clause}")

#     # 검색 실행
#     logger.info(f"컬렉션 '{self.collection_name}'에서 필터링 검색 실행 중...")
#     results = self.collection.query(where=where_clause, n_results=n_results, include=["documents", "metadatas"])

#     # 결과 로깅
#     if results['documents'] and results['documents'][0]:
#       logger.info(f"필터링 검색 결과: {len(results['documents'][0])}개 항목 발견")
#     else:
#       logger.warning(f"필터링 검색 결과가 비어 있습니다. 컬렉션 '{self.collection_name}'에 데이터가 있는지 확인하세요.")

#     # 결과 형식 변환
#     formatted_results = []
#     for i, (doc, metadata) in enumerate(
#         zip(results['documents'][0] if results['documents'] and results['documents'][0] else [],
#             results['metadatas'][0] if results['metadatas'] and results['metadatas'][0] else [])):
#       formatted_results.append({
#           "rank": i + 1,
#           "corp_name": metadata['corp_name'],
#           "corp_code": metadata['corp_code'],
#           "market_type": metadata['market_type'],
#           "industry_name": metadata['industry_name'],
#           "document": doc,
#           "metadata": metadata
#       })

#     return {
#         "filter_criteria": {
#             "industry": industry,
#             "min_revenue": min_revenue,
#             "max_debt_ratio": max_debt_ratio
#         },
#         "results": formatted_results
#     }

#endregion

import logging
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue, Range
from voyageai import Client as VoyageClient
from dotenv import load_dotenv

from app.core.config import settings

# 로깅 설정
logger = logging.getLogger(__name__)


# ✅ 사용자 조건에 따라 Qdrant 필터 객체 생성
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


# ✅ Qdrant + Voyage 기반 벡터 검색 리포지토리
class VectorStoreRepository:
    def __init__(self):
        self.qdrant = QdrantClient(
            url=settings.VECTOR_STORE_PATH,
            api_key=settings.QDRANT_API_KEY,
            prefer_grpc=False
        )
        self.voyage = VoyageClient(api_key=settings.VOYAGE_API_KEY)
        self.collection_name = "financial_data"
        
    # ✅ 0. CSV 데이터로 벡터 스토어 초기화
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
                        "id": f"{i+j}",
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

    # ✅ 1. 유사도 기반 검색
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

    # ✅ 2. 조건 기반 필터 검색
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

    # ✅ 3. 유사도 + 필터 조합 검색
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
