import os
import logging
from typing import Dict, Any, List, Optional
from tavily import TavilyClient
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)

class TavilySearchService:
    """
    Tavily API를 사용하여 회사 정보를 검색하고 긍정적/부정적 요소를 추출하는 서비스
    """
    
    def __init__(self):
        """
        Tavily 클라이언트 초기화
        """
        self.api_key = os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            logger.warning("TAVILY_API_KEY가 설정되지 않았습니다. Tavily 검색 기능을 사용할 수 없습니다.")
        self.client = TavilyClient(api_key=self.api_key) if self.api_key else None
    
    async def search_company_factors(self, company_name: str, industry_name: Optional[str] = None) -> Dict[str, List[str]]:
        """
        회사명과 산업명을 기반으로 회사의 긍정적/부정적 요소를 검색
        
        Args:
            company_name (str): 회사명
            industry_name (Optional[str]): 산업명
            
        Returns:
            Dict[str, List[str]]: 긍정적 요소와 부정적 요소를 포함한 딕셔너리
        """
        if not self.client:
            logger.warning("Tavily 클라이언트가 초기화되지 않았습니다.")
            return {"positive_factors": [], "negative_factors": []}
        
        try:
            # 검색 쿼리 구성
            search_query = f"{company_name} 기업 분석 긍정적 요소 부정적 요소"
            if industry_name:
                search_query += f" {industry_name} 산업"
            
            logger.info(f"Tavily 검색 쿼리: {search_query}")
            
            # Tavily 검색 실행
            search_result = self.client.search(
                query=search_query,
                search_depth="advanced",
                include_answer=True,
                include_raw_content=False,
                max_tokens=8000,
                max_results=5
            )
            
            # 검색 결과에서 긍정적/부정적 요소 추출
            answer = search_result.get("answer", "")
            
            # 긍정적 요소와 부정적 요소 추출을 위한 프롬프트 구성
            extraction_prompt = f"""
            다음은 {company_name} 기업에 대한 검색 결과입니다:
            
            {answer}
            
            위 내용에서 {company_name}의 긍정적 요소와 부정적 요소를 각각 3-5개씩 추출해주세요.
            긍정적 요소는 기업의 강점, 성장 가능성, 경쟁력 등을 나타내는 요소입니다.
            부정적 요소는 기업의 약점, 위험 요소, 도전 과제 등을 나타내는 요소입니다.
            
            결과는 다음 형식으로 제공해주세요:
            
            [긍정적 요소]
            - 요소 1
            - 요소 2
            - 요소 3
            
            [부정적 요소]
            - 요소 1
            - 요소 2
            - 요소 3
            """
            
            # Tavily를 사용하여 요소 추출
            extraction_result = self.client.qna_search(
                query=extraction_prompt,
                search_depth="advanced",
                max_tokens=4000
            )
            
            extracted_answer = extraction_result.get("answer", "")
            
            # 추출된 결과 파싱
            positive_factors = []
            negative_factors = []
            
            current_section = None
            for line in extracted_answer.split("\n"):
                line = line.strip()
                if "[긍정적 요소]" in line:
                    current_section = "positive"
                elif "[부정적 요소]" in line:
                    current_section = "negative"
                elif line.startswith("- ") and current_section:
                    factor = line[2:].strip()
                    if factor:
                        if current_section == "positive":
                            positive_factors.append(factor)
                        else:
                            negative_factors.append(factor)
            
            logger.info(f"Tavily 검색 결과 - 긍정적 요소: {len(positive_factors)}개, 부정적 요소: {len(negative_factors)}개")
            
            return {
                "positive_factors": positive_factors,
                "negative_factors": negative_factors
            }
            
        except Exception as e:
            logger.error(f"Tavily 검색 중 오류 발생: {str(e)}")
            return {"positive_factors": [], "negative_factors": []}
