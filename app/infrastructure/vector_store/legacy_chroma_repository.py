"""
레거시 Chroma 기반 벡터 저장소 구현

이 파일은 Chroma DB를 사용한 이전 버전의 벡터 저장소 구현을 보존합니다.
현재 프로젝트는 Qdrant로 마이그레이션되었으므로 이 코드는 더 이상 사용되지 않습니다.
참조 및 기록 목적으로 유지됩니다.
"""

import logging
import os
from typing import List, Dict, Optional

import chromadb
import pandas as pd
import voyageai
from dotenv import load_dotenv

# 로깅 설정
logger = logging.getLogger(__name__)


class ChromaVectorStoreRepository:
    """
    재무제표 데이터의 벡터 저장소 관리를 위한 리포지토리 클래스
    VoyageAI와 ChromaDB를 사용하여 구현
    """

    def __init__(self, api_key=None):
        # .env 파일 로드
        load_dotenv()
        # 환경 변수에서 VoyageAI API 키 가져오기 또는 매개변수로 전달된 키 사용
        self.api_key = api_key or os.getenv("VOYAGE_API_KEY")

        # API 키 로깅 (마스킹 처리)
        if self.api_key:
            masked_key = self.api_key[:4] + "*" * (len(self.api_key) - 8) + self.api_key[-4:] if len(
                self.api_key) > 8 else "****"
            logger.info(f"VoyageAI API 키 로드됨: {masked_key}")
        else:
            logger.error("VoyageAI API 키를 찾을 수 없습니다!")

        # VoyageAI 클라이언트 초기화 및 전역 API 키 설정
        voyageai.api_key = self.api_key  # 전역 API 키 설정 추가
        self.voyage_client = voyageai.Client(api_key=self.api_key)

        # ChromaDB 클라이언트 초기화
        self.persist_directory = "data/vector_store"
        os.makedirs(self.persist_directory, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path=self.persist_directory)

        # 기본 컬렉션 이름
        self.collection_name = "korean_financial_data"

        # 컬렉션 초기화 또는 로드
        self._initialize_collection()

    def _initialize_collection(self):
        """
        ChromaDB 컬렉션 초기화 또는 기존 컬렉션 로드
        """
        try:
            # 기존 컬렉션이 있으면 로드
            self.collection = self.chroma_client.get_collection(name=self.collection_name)
            logger.info(f"기존 컬렉션 '{self.collection_name}' 로드됨")
        except Exception:
            # 없으면 새로 생성
            self.collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}  # 코사인 유사도 사용
            )
            logger.info(f"새 컬렉션 '{self.collection_name}' 생성됨")

    def _generate_embeddings(self, texts: List[str], model: str = "voyage-finance-2") -> List[List[float]]:
        """
        VoyageAI를 사용하여 텍스트의 임베딩 생성

        Args:
            texts: 임베딩할 텍스트 목록
            model: 사용할 임베딩 모델 이름

        Returns:
            List[List[float]]: 임베딩 벡터 목록
        """
        logger.info(f"{len(texts)}개 텍스트에 대한 임베딩 생성 중...")

        # 배치 사이즈를 128로 제한 (Voyage API 제한)
        batch_size = 128
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            logger.info(f"배치 처리 중: {i} ~ {i+len(batch_texts)-1}")

            try:
                response = self.voyage_client.embed(texts=batch_texts, model=model, input_type="document")
                batch_embeddings = response.embeddings
                all_embeddings.extend(batch_embeddings)
                logger.info(f"배치 {i//batch_size + 1} 임베딩 완료: {len(batch_embeddings)}개")
            except Exception as e:
                logger.error(f"임베딩 생성 중 오류 발생: {str(e)}")
                # 오류 발생 시 빈 임베딩으로 대체 (실제 구현에서는 적절한 오류 처리 필요)
                empty_embeddings = [[0.0] * 1024 for _ in range(len(batch_texts))]
                all_embeddings.extend(empty_embeddings)

        logger.info(f"총 {len(all_embeddings)}개 임베딩 생성 완료")
        return all_embeddings

    def build_vector_store(self, csv_path: str, collection_name: Optional[str] = None,
                           embedding_model: str = "voyage-finance-2"):
        """
        CSV 파일에서 재무제표 데이터를 로드하고 벡터 저장소 구축

        Args:
            csv_path: CSV 파일 경로
            collection_name: 생성할 컬렉션 이름 (None이면 기본값 사용)
            embedding_model: 임베딩 모델 이름
        """
        # 컬렉션 이름 설정
        if collection_name:
            self.collection_name = collection_name

        # CSV 파일 로드
        logger.info(f"CSV 파일 로드 중: {csv_path}")
        try:
            df = pd.read_csv(csv_path)
            logger.info(f"CSV 로드 완료: {len(df)}개 행")
        except Exception as e:
            logger.error(f"CSV 파일 로드 중 오류 발생: {str(e)}")
            return

        # 필수 컬럼 확인
        required_columns = ['corp_code', 'corp_name', 'market_type', 'industry_name']
        for col in required_columns:
            if col not in df.columns:
                logger.error(f"필수 컬럼 누락: {col}")
                return

        # 기존 컬렉션 삭제 (있는 경우)
        try:
            self.chroma_client.delete_collection(name=self.collection_name)
            logger.info(f"기존 컬렉션 '{self.collection_name}' 삭제됨")
        except:
            pass

        # 새 컬렉션 생성
        self.collection = self.chroma_client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"새 컬렉션 '{self.collection_name}' 생성됨")

        # 회사 설명 텍스트 생성
        logger.info("회사 설명 텍스트 생성 중...")
        df['description'] = df.apply(
            lambda row: f"{row['corp_name']} - {row['industry_name']} - {row['market_type']}", axis=1)
        descriptions = df['description'].tolist()

        # 임베딩 생성
        embeddings = self._generate_embeddings(descriptions, model=embedding_model)

        # 메타데이터 생성
        metadatas = []
        for _, row in df.iterrows():
            metadata = {}
            for col in df.columns:
                # NaN 값 처리
                if pd.isna(row[col]):
                    metadata[col] = None
                else:
                    metadata[col] = row[col]
            metadatas.append(metadata)

        # 문서 ID 생성
        ids = [f"doc_{i}" for i in range(len(descriptions))]

        # ChromaDB에 저장
        logger.info("ChromaDB에 저장 중...")
        self.collection.add(
            embeddings=embeddings,
            documents=descriptions,
            metadatas=metadatas,
            ids=ids
        )
        logger.info(f"벡터 저장소 구축 완료: {len(descriptions)}개 문서 저장됨")

    async def search_similar_companies(self, query: str, n_results: int = 8,
                                       embedding_model: str = "voyage-finance-2"):
        """
        쿼리와 유사한 회사 검색

        Args:
            query: 검색 쿼리
            n_results: 반환할 결과 수
            embedding_model: 임베딩 모델 이름

        Returns:
            Dict: 검색 결과
        """
        logger.info(f"쿼리: '{query}' 검색 중...")

        # 쿼리 임베딩 생성
        query_embedding = self.voyage_client.embed(
            texts=[query],
            model=embedding_model,
            input_type="query"
        ).embeddings[0]

        # 벡터 검색 실행
        logger.info(f"컬렉션 '{self.collection_name}'에서 검색 실행 중...")
        results = self.collection.query(query_embeddings=[query_embedding],
                                        n_results=n_results,
                                        include=["documents", "metadatas", "distances"])

        # 결과 형식화
        formatted_results = []
        for i in range(len(results['ids'][0])):
            metadata = results['metadatas'][0][i]
            formatted_results.append({
                "corp_code": metadata.get("corp_code"),
                "corp_name": metadata.get("corp_name"),
                "market_type": metadata.get("market_type"),
                "industry_name": metadata.get("industry_name"),
                "similarity": 1 - results['distances'][0][i],  # 코사인 거리를 유사도로 변환
                "metadata": metadata
            })

        return {
            "query": query,
            "results": formatted_results
        }
