"""
LangGraph 에이전트 그래프 시각화 테스트
"""
import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.domain.report_generation.agent import ReportAgent
from app.domain.report_generation.prompts import DEFAULT_SECTIONS

def print_agent_graph_structure():
    """에이전트 그래프 구조를 출력합니다."""
    agent = ReportAgent()
    
    print("\n=== 에이전트 그래프 구조 ===")
    print("1. 노드:")
    print("   - START")
    print("   - calculate_ratios: 추가 재무비율 계산")
    print("   - generate_summary: 요약 카드 생성")
    print("   - analyze_section: 섹션 분석")
    print("   - compile_report: 최종 보고서 컴파일")
    print("   - END")
    
    print("\n2. 엣지:")
    print("   - START → calculate_ratios")
    print("   - calculate_ratios → generate_summary")
    print("   - generate_summary → analyze_section")
    print("   - analyze_section → analyze_section (조건: _should_continue_analysis가 True 반환)")
    print("   - analyze_section → compile_report (조건: _should_continue_analysis가 False 반환)")
    print("   - compile_report → END")
    
    print("\n3. 섹션 정보:")
    for i, section in enumerate(DEFAULT_SECTIONS):
        print(f"   {i+1}. {section['name']}: {section['description']}")

if __name__ == "__main__":
    print_agent_graph_structure()
