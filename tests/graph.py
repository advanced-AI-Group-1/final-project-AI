from IPython.display import Image, display
from langgraph.graph.state import CompiledStateGraph


def visualize_graph(graph, xray=False):
  """
  CompiledStateGraph 객체를 시각화하여 표시합니다.

  이 함수는 주어진 그래프 객체가 CompiledStateGraph 인스턴스인 경우
  해당 그래프를 Mermaid 형식의 PNG 이미지로 변환하여 표시합니다.

  Args:
      graph: 시각화할 그래프 객체. CompiledStateGraph 인스턴스여야 합니다.

  Returns:
      None

  Raises:
      Exception: 그래프 시각화 과정에서 오류가 발생한 경우 예외를 출력합니다.
  """
  try:
    # 그래프 시각화
    if isinstance(graph, CompiledStateGraph):
      display(
        Image(
          graph.get_graph(xray=xray).draw_mermaid_png(
            background_color="white",
            node_colors=NodeStyles(),
          )
        )
      )
  except Exception as e:
    print(f"[ERROR] Visualize Graph Error: {e}")
