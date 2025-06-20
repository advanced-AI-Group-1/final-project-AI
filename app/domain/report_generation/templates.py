"""
보고서 생성에 필요한 HTML 템플릿과 마크다운 변환 기능을 제공하는 모듈
"""
import re


def get_html_template() -> str:
  """HTML 보고서 템플릿"""
  return """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{company_name} 신용분석보고서</title>
        <style>
            body {{
                font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f8f9fa;
                font-weight: normal; /* 기본 폰트 웨이트 명시 */
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 10px;
                margin-bottom: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 2.5em;
                font-weight: bold; /* 제목만 볼드 */
            }}
            .header .subtitle {{
                font-size: 1.2em;
                margin-top: 10px;
                opacity: 0.9;
                font-weight: normal; /* 부제목은 일반 */
            }}
            .summary-card {{
                background: white;
                border-radius: 10px;
                padding: 30px;
                margin-bottom: 30px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                border-left: 5px solid #667eea;
            }}
            .detailed-report {{
                background: white;
                border-radius: 10px;
                padding: 30px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            h2 {{
                color: #2c3e50;
                border-bottom: 3px solid #667eea;
                padding-bottom: 10px;
                margin-top: 30px;
                font-weight: bold; /* h2만 볼드 */
            }}
            h3 {{
                color: #34495e;
                margin-top: 25px;
                font-weight: 600; /* h3는 약간 굵게 */
            }}
            p {{
                font-weight: normal; /* 문단은 일반 */
                margin-bottom: 15px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                background: white;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 12px;
                text-align: center;
                font-weight: normal; /* 테이블 셀은 일반 */
            }}
            th {{
                background-color: #667eea;
                color: white;
                font-weight: bold; /* 테이블 헤더만 볼드 */
            }}
            tr:nth-child(even) {{
                background-color: #f2f2f2;
            }}
            .rating-badge {{
                display: inline-block;
                background: #28a745;
                color: white;
                padding: 5px 15px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 1.1em;
            }}
            .keyword {{
                display: inline-block;
                background: #17a2b8;
                color: white;
                padding: 3px 10px;
                border-radius: 15px;
                margin: 2px;
                font-size: 0.9em;
                font-weight: normal; /* 키워드는 일반 */
            }}
            .metric {{
                background: #e9ecef;
                padding: 15px;
                border-radius: 5px;
                margin: 10px 0;
                font-weight: normal; /* 메트릭 전체는 일반 */
            }}
            .metric strong {{
                color: #495057;
                font-weight: bold; /* strong 태그만 볼드 */
            }}
            .footer {{
                text-align: center;
                margin-top: 40px;
                padding: 20px;
                color: #6c757d;
                font-size: 0.9em;
                font-weight: normal; /* 푸터는 일반 */
            }}
            .section {{
                margin-bottom: 40px;
            }}
            /* 강조 텍스트 스타일 */
            strong {{
                font-weight: bold;
                color: #2c3e50;
            }}
            em {{
                font-style: italic;
                font-weight: normal;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{company_name} 신용분석보고서</h1>
            <div class="subtitle">{industry_name} | {market_type}</div>
        </div>

        <div class="summary-card">
            {summary_content}
        </div>

        <div class="detailed-report">
            {detailed_content}
        </div>

        <div class="footer">
            <p>본 보고서는 제공된 재무 데이터를 기반으로 AI가 생성한 분석 보고서입니다.</p>
            <p>보고서 생성일: {generation_date}</p>
        </div>
    </body>
    </html>
    """


def markdown_to_html(markdown_text: str) -> str:
  """마크다운을 HTML로 변환 (수정된 버전)"""
  html = markdown_text
  
  # **텍스트** 볼드 변환 (정규식으로 정확하게)
  html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
  
  # *텍스트* 이탤릭 변환 (정규식으로 정확하게)
  html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
  
  # 헤더 변환 (수정)
  html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
  html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
  
  # 테이블 변환 (개선된 로직)
  lines = html.split('\n')
  new_lines = []
  in_table = False
  
  for i, line in enumerate(lines):
    line = line.strip()
    
    if '|' in line and not line.startswith('#'):
      if not in_table:
        new_lines.append('<table>')
        in_table = True
      
      # 구분선 건너뛰기
      if '---' in line or '===' in line:
        continue
      
      cells = [cell.strip() for cell in line.split('|')]
      # 빈 셀 제거 (양 끝의 빈 셀)
      if cells and cells[0] == '':
        cells = cells[1:]
      if cells and cells[-1] == '':
        cells = cells[:-1]
      
      if len(cells) > 0:
        # 다음 줄이 구분선인지 확인하여 헤더 여부 결정
        is_header = False
        if i + 1 < len(lines):
          next_line = lines[i + 1].strip()
          if '---' in next_line or '===' in next_line:
            is_header = True
        
        if is_header:
          row = '<tr>' + ''.join([f'<th>{cell}</th>' for cell in cells]) + '</tr>'
        else:
          row = '<tr>' + ''.join([f'<td>{cell}</td>' for cell in cells]) + '</tr>'
        new_lines.append(row)
    else:
      if in_table:
        new_lines.append('</table>')
        in_table = False
      
      # 빈 줄이 아닌 경우에만 추가
      if line:
        new_lines.append(line)
  
  if in_table:
    new_lines.append('</table>')
  
  html = '\n'.join(new_lines)
  
  # 문단 변환 (개선)
  paragraphs = html.split('\n\n')
  html_paragraphs = []
  
  for p in paragraphs:
    p = p.strip()
    if p and not any(
        p.startswith(tag) for tag in ['<h', '<table', '<tr', '<th', '<td', '<strong', '<em']):
      # 이미 HTML 태그가 아닌 경우에만 p 태그로 감싸기
      if not p.startswith('<') and not p.endswith('>'):
        html_paragraphs.append(f'<p>{p}</p>')
      else:
        html_paragraphs.append(p)
    elif p:
      html_paragraphs.append(p)
  
  return '\n'.join(html_paragraphs)


def generate_html_report(company_name: str, summary_card: str, detailed_report: str,
    generated_at: str) -> str:
  """HTML 보고서 생성"""
  template = get_html_template()
  generation_date = generated_at.split("T")[0].replace("-", "년 ", 1).replace("-", "월 ", 1) + "일"
  
  # 업종 및 시장 정보가 없는 경우 기본값 설정
  industry_name = "금융 분석"
  market_type = "신용평가"
  
  # 마크다운 내용을 HTML로 변환
  summary_html = markdown_to_html(summary_card)
  detailed_html = markdown_to_html(detailed_report)
  
  # 템플릿에 내용 삽입
  html_report = template.format(
    company_name=company_name,
    industry_name=industry_name,
    market_type=market_type,
    summary_content=summary_html,
    detailed_content=detailed_html,
    generation_date=generation_date
  )
  
  return html_report
