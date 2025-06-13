from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import os
import json

class FinancialStatement(BaseModel):
    """재무제표 데이터 모델"""
    year: int
    quarter: Optional[int] = None
    revenue: float
    operating_profit: float
    net_income: float
    total_assets: float
    total_liabilities: float
    total_equity: float
    cash_flow_operating: float
    cash_flow_investing: float
    cash_flow_financing: float
    
class FinancialDataModel:
    """재무제표 데이터 관리 모델"""
    
    # 데이터 저장 경로
    DATA_DIR = "data/financial_statements"
    
    @classmethod
    async def get_financial_data_by_id(cls, document_id: str) -> Dict[str, Any]:
        """
        문서 ID를 기반으로 재무제표 데이터를 조회합니다.
        
        Args:
            document_id (str): 문서 ID
            
        Returns:
            Dict[str, Any]: 재무제표 데이터
        """
        # 데이터 디렉토리 확인 및 생성
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        
        # 문서 ID에 해당하는 파일 경로
        file_path = os.path.join(cls.DATA_DIR, f"{document_id}.json")
        
        # 파일이 존재하는지 확인
        if not os.path.exists(file_path):
            # 파일이 없는 경우 빈 데이터 반환
            return {
                "company_name": "Unknown",
                "document_id": document_id,
                "financial_statements": {}
            }
        
        # 파일에서 데이터 로드
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        return data
        
    @classmethod
    async def save_financial_data(cls, company_data: Dict[str, Any]) -> str:
        """
        재무제표 데이터를 저장합니다.
        
        Args:
            company_data (Dict[str, Any]): 저장할 기업 재무제표 데이터
            
        Returns:
            str: 저장된 문서 ID
        """
        # 데이터 디렉토리 확인 및 생성
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        
        # 문서 ID 생성 또는 가져오기
        document_id = company_data.get("document_id", f"{company_data['company_name'].replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        company_data["document_id"] = document_id
        
        # 파일 경로
        file_path = os.path.join(cls.DATA_DIR, f"{document_id}.json")
        
        # 데이터 저장
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(company_data, f, ensure_ascii=False, indent=2)
            
        return document_id
        
    @classmethod
    async def get_all_companies(cls) -> List[Dict[str, Any]]:
        """
        모든 기업 데이터의 목록을 반환합니다.
        
        Returns:
            List[Dict[str, Any]]: 기업 데이터 목록
        """
        # 데이터 디렉토리 확인 및 생성
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        
        companies = []
        
        # 디렉토리 내 모든 JSON 파일 읽기
        for filename in os.listdir(cls.DATA_DIR):
            if filename.endswith('.json'):
                file_path = os.path.join(cls.DATA_DIR, filename)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # 기본 정보만 추출
                company_info = {
                    "company_name": data.get("company_name", "Unknown"),
                    "document_id": data.get("document_id", filename.replace('.json', '')),
                    "industry": data.get("industry", "Unknown"),
                    "last_updated": data.get("last_updated", "Unknown")
                }
                
                companies.append(company_info)
                
        return companies
