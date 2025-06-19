import logging
import os
from typing import List, Dict, Optional

import chromadb
import pandas as pd
import voyageai
from dotenv import load_dotenv

# 로깅 설정
logger = logging.getLogger(__name__)


class VectorStoreRepository:
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
      logger.info(f"컬렉션 '{self.collection_name}'을 로드하려고 시도합니다.")
      self.collection = self.chroma_client.get_collection(name=self.collection_name)
      logger.info(f"컬렉션 '{self.collection_name}'을 성공적으로 로드했습니다.")
    except Exception as e:
      logger.error(f"컬렉션 '{self.collection_name}' 로드 중 오류 발생: {str(e)}")
      logger.info(f"새 컬렉션 '{self.collection_name}'을 생성합니다.")
      self.collection = self.chroma_client.create_collection(
          name=self.collection_name, metadata={"description": "Korean financial data with embeddings"})
      logger.info(f"새 컬렉션 '{self.collection_name}'이 성공적으로 생성되었습니다.")

  def create_text_representation(self, row: pd.Series) -> str:
    """
            각 행의 데이터를 자연어 텍스트로 변환
            
            Args:
                row (pd.Series): 재무 데이터 행
                
            Returns:
                str: 텍스트 표현
            """
    text_parts = []

    # 기본 회사 정보
    text_parts.append(f"회사명: {row['corp_name']}")
    text_parts.append(f"시장구분: {row['market_type']}")
    text_parts.append(f"업종: {row['industry_name']}")

    # 재무 정보 (억원 단위로 표현)
    if pd.notna(row['revenue']):
      text_parts.append(f"매출액: {row['revenue'] / 100000000:.1f}억원")
    if pd.notna(row['operating_profit']):
      text_parts.append(f"영업이익: {row['operating_profit'] / 100000000:.1f}억원")
    if pd.notna(row['net_income']):
      text_parts.append(f"당기순이익: {row['net_income'] / 100000000:.1f}억원")
    if pd.notna(row['total_assets']):
      text_parts.append(f"총자산: {row['total_assets'] / 100000000:.1f}억원")
    if pd.notna(row['total_liabilities']):
      text_parts.append(f"총부채: {row['total_liabilities'] / 100000000:.1f}억원")
    if pd.notna(row['total_equity']):
      text_parts.append(f"자본총계: {row['total_equity'] / 100000000:.1f}억원")

    # 재무 비율
    if pd.notna(row['debt_ratio']):
      text_parts.append(f"부채비율: {row['debt_ratio']:.2f}%")
    if pd.notna(row['ROA']):
      text_parts.append(f"ROA: {row['ROA']:.2f}%")
    if pd.notna(row['ROE']):
      text_parts.append(f"ROE: {row['ROE']:.2f}%")
    if pd.notna(row['asset_turnover_ratio']):
      text_parts.append(f"매출총자산회전율: {row['asset_turnover_ratio']:.2f}")

    return " | ".join(text_parts)

  def embed_with_voyage(self, texts: List[str], model: str = "voyage-3") -> List[List[float]]:
    """
            Voyage AI를 사용하여 텍스트 임베딩
            
            Args:
                texts (List[str]): 임베딩할 텍스트 목록
                model (str): 사용할 임베딩 모델
                
            Returns:
                List[List[float]]: 임베딩 벡터 목록
            """
    # 배치 사이즈를 128로 제한 (Voyage API 제한)
    batch_size = 128
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
      batch = texts[i:i + batch_size]

      # Voyage Finance 2 사용 시
      if model == "voyage-finance-2":
        response = self.voyage_client.embed(
            texts=batch,
            model="voyage-finance-2",
            input_type="document"  # 문서 임베딩용
        )
      else:  # voyage-3 사용 시
        response = self.voyage_client.embed(texts=batch, model="voyage-3", input_type="document")

      all_embeddings.extend(response.embeddings)

    return all_embeddings

  def build_vector_store(self, csv_path: str, collection_name: Optional[str] = None, embedding_model: str = "voyage-3"):
    """
            CSV 파일에서 데이터를 로드하여 벡터 스토어 구축
            
            Args:
                csv_path (str): CSV 파일 경로
                collection_name (Optional[str]): 컬렉션 이름 (없으면 기본값 사용)
                embedding_model (str): 사용할 임베딩 모델
            """
    # 컬렉션 이름 설정
    if collection_name:
      self.collection_name = collection_name
      self._initialize_collection()

    # CSV 파일 로드
    df = pd.read_csv(csv_path)

    # 결측값 처리
    df = df.fillna("")

    # 기존 컬렉션이 있으면 삭제하고 새로 생성
    try:
      self.chroma_client.delete_collection(name=self.collection_name)
    except:
      pass

    self.collection = self.chroma_client.create_collection(
        name=self.collection_name, metadata={"description": "Korean financial data with embeddings"})

    # 텍스트 표현 생성
    logger.info("텍스트 표현 생성 중...")
    texts = []
    metadatas = []
    ids = []

    for idx, row in df.iterrows():
      # 텍스트 표현 생성
      text = self.create_text_representation(row)
      texts.append(text)

      # 메타데이터 준비 (검색 시 필터링용)
      metadata = {
          "corp_code": str(row['corp_code']),
          "corp_name": row['corp_name'],
          "market_type": row['market_type'],
          "industry_name": row['industry_name'],
          "is_consolidated": str(row['is_consolidated'])
      }

      # 모든 수치 데이터를 메타데이터에 포함
      for col in df.columns:
        if col not in ['corp_code', 'corp_name', 'market_type', 'industry_name', 'is_consolidated']:
          if pd.notna(row[col]) and row[col] != "":
            try:
              metadata[col] = float(row[col])
            except (ValueError, TypeError):
              # 숫자로 변환할 수 없는 경우 문자열로 저장
              if pd.notna(row[col]):
                metadata[col] = str(row[col])

      metadatas.append(metadata)
      ids.append(f"corp_{row['corp_code']}")

    # 임베딩 생성
    logger.info(f"{embedding_model}로 임베딩 생성 중...")
    embeddings = self.embed_with_voyage(texts, model=embedding_model)

    # ChromaDB에 저장
    logger.info("ChromaDB에 저장 중...")
    self.collection.add(embeddings=embeddings, documents=texts, metadatas=metadatas, ids=ids)

    logger.info(f"총 {len(texts)}개 레코드가 성공적으로 저장되었습니다.")
    return self.collection

  async def search_similar_companies(self, query: str, n_results: int = 5, embedding_model: str = "voyage-3"):
    """
            쿼리와 유사한 회사 검색
            
            Args:
                query (str): 검색 쿼리
                n_results (int): 반환할 결과 수
                embedding_model (str): 사용할 임베딩 모델
                
            Returns:
                Dict: 검색 결과
            """
    logger.info(f"검색 쿼리: '{query}', 컬렉션 이름: '{self.collection_name}'")

    # 컬렉션이 제대로 초기화되었는지 확인
    if not hasattr(self, 'collection') or self.collection is None:
      logger.error("컬렉션이 초기화되지 않았습니다. _initialize_collection 메서드를 호출합니다.")
      self._initialize_collection()

    # 쿼리 임베딩
    logger.info(f"{embedding_model} 모델을 사용하여 쿼리 임베딩 생성 중...")
    if embedding_model == "voyage-finance-2":
      query_embedding = self.voyage_client.embed(
          texts=[query],
          model="voyage-finance-2",
          input_type="query"  # 쿼리 임베딩용
      ).embeddings[0]
    else:
      query_embedding = \
        self.voyage_client.embed(texts=[query], model="voyage-3", input_type="query").embeddings[0]

    # 검색 실행
    logger.info(f"컬렉션 '{self.collection_name}'에서 검색 실행 중...")
    results = self.collection.query(query_embeddings=[query_embedding],
                                    n_results=n_results,
                                    include=["documents", "metadatas", "distances"])

    # 결과 로깅
    if results['documents'] and results['documents'][0]:
      logger.info(f"검색 결과: {len(results['documents'][0])}개 항목 발견")
    else:
      logger.warning(f"검색 결과가 비어 있습니다. 컬렉션 '{self.collection_name}'에 데이터가 있는지 확인하세요.")

    # 결과 형식 변환
    formatted_results = []
    for i, (doc, metadata, distance) in enumerate(
        zip(results['documents'][0] if results['documents'] and results['documents'][0] else [],
            results['metadatas'][0] if results['metadatas'] and results['metadatas'][0] else [],
            results['distances'][0] if results['distances'] and results['distances'][0] else [])):
      similarity = 1 - distance  # 거리를 유사도로 변환
      formatted_results.append({
          "rank": i + 1,
          "corp_name": metadata['corp_name'],
          "corp_code": metadata['corp_code'],
          "market_type": metadata['market_type'],
          "industry_name": metadata['industry_name'],
          "document": doc,
          "similarity": similarity,
          "metadata": metadata
      })

    return {"query": query, "results": formatted_results}

  async def filter_search(self,
                          industry: str = None,
                          min_revenue: float = None,
                          max_debt_ratio: float = None,
                          n_results: int = 5):
    """
            조건부 필터링 검색
            
            Args:
                industry (str): 업종
                min_revenue (float): 최소 매출액
                max_debt_ratio (float): 최대 부채비율
                n_results (int): 반환할 결과 수
                
            Returns:
                Dict: 검색 결과
            """
    logger.info(f"필터링 검색 시작, 컬렉션 이름: '{self.collection_name}'")

    # 컬렉션이 제대로 초기화되었는지 확인
    if not hasattr(self, 'collection') or self.collection is None:
      logger.error("컬렉션이 초기화되지 않았습니다. _initialize_collection 메서드를 호출합니다.")
      self._initialize_collection()

    # 필터 구성
    where_clause = {}

    if industry:
      where_clause["industry_name"] = industry
      logger.info(f"업종 필터 적용: {industry}")

    if min_revenue:
      where_clause["revenue"] = {"$gte": min_revenue}
      logger.info(f"최소 매출액 필터 적용: {min_revenue}")

    if max_debt_ratio:
      where_clause["debt_ratio"] = {"$lte": max_debt_ratio}
      logger.info(f"최대 부채비율 필터 적용: {max_debt_ratio}")

    logger.info(f"필터 조건: {where_clause}")

    # 검색 실행
    logger.info(f"컬렉션 '{self.collection_name}'에서 필터링 검색 실행 중...")
    results = self.collection.query(where=where_clause, n_results=n_results, include=["documents", "metadatas"])

    # 결과 로깅
    if results['documents'] and results['documents'][0]:
      logger.info(f"필터링 검색 결과: {len(results['documents'][0])}개 항목 발견")
    else:
      logger.warning(f"필터링 검색 결과가 비어 있습니다. 컬렉션 '{self.collection_name}'에 데이터가 있는지 확인하세요.")

    # 결과 형식 변환
    formatted_results = []
    for i, (doc, metadata) in enumerate(
        zip(results['documents'][0] if results['documents'] and results['documents'][0] else [],
            results['metadatas'][0] if results['metadatas'] and results['metadatas'][0] else [])):
      formatted_results.append({
          "rank": i + 1,
          "corp_name": metadata['corp_name'],
          "corp_code": metadata['corp_code'],
          "market_type": metadata['market_type'],
          "industry_name": metadata['industry_name'],
          "document": doc,
          "metadata": metadata
      })

    return {
        "filter_criteria": {
            "industry": industry,
            "min_revenue": min_revenue,
            "max_debt_ratio": max_debt_ratio
        },
        "results": formatted_results
    }
