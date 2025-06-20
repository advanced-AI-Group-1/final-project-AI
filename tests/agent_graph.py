import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.domain.report_generation.agent import ReportAgent


def test_agent_graph():
  agent = ReportAgent()
  graph = agent._create_workflow()
  return graph


from graph import visualize_graph


def print_agent_graph_structure():
  graph = test_agent_graph()
  visualize_graph(graph)
  return


if __name__ == '__main__':
  print_agent_graph_structure()
