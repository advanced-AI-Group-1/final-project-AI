"""
보고서 생성에 필요한 HTML 템플릿과 마크다운 변환 기능을 제공하는 모듈
"""
from datetime import datetime


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
                font-weight: bold;
            }}
            .header .subtitle {{
                font-size: 1.2em;
                margin-top: 10px;
                opacity: 0.9;
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
            }}
            h3 {{
                color: #34495e;
                margin-top: 25px;
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
            }}
            th {{
                background-color: #667eea;
                color: white;
                font-weight: bold;
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
            }}
            .metric {{
                background: #e9ecef;
                padding: 15px;
                border-radius: 5px;
                margin: 10px 0;
            }}
            .metric strong {{
                color: #495057;
            }}
            .footer {{
                text-align: center;
                margin-top: 40px;
                padding: 20px;
                color: #6c757d;
                font-size: 0.9em;
            }}
            .section {{
                margin-bottom: 40px;
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
  """마크다운을 HTML로 변환"""
  html = markdown_text

  # 헤더 변환
  html = html.replace('## ', '<h2>').replace('\n\n', '</h2>\n\n')
  html = html.replace('### ', '<h3>').replace('\n\n', '</h3>\n\n')

  # 테이블 변환 (간단히)
  lines = html.split('\n')
  new_lines = []
  in_table = False

  for line in lines:
    if '|' in line and not line.strip().startswith('#'):
      if not in_table:
        new_lines.append('<table>')
        in_table = True

      if '---' in line:
        continue

      cells = [cell.strip() for cell in line.split('|') if cell.strip()]
      if len(cells) > 0:
        if '**' in line:  # 헤더 행
          row = '<tr>' + ''.join([f'<th>{cell.replace("**", "")}</th>' for cell in cells]) + '</tr>'
        else:
          row = '<tr>' + ''.join([f'<td>{cell}</td>' for cell in cells]) + '</tr>'
        new_lines.append(row)
    else:
      if in_table:
        new_lines.append('</table>')
        in_table = False
      new_lines.append(line)

  if in_table:
    new_lines.append('</table>')

  html = '\n'.join(new_lines)

  # 강조 텍스트
  html = html.replace('**', '<strong>').replace('**', '</strong>')
  html = html.replace('*', '<em>').replace('*', '</em>')

  # 문단 변환
  paragraphs = html.split('\n\n')
  html_paragraphs = []

  for p in paragraphs:
    p = p.strip()
    if p and not p.startswith('<'):
      html_paragraphs.append(f'<p>{p}</p>')
    else:
      html_paragraphs.append(p)

  return '\n'.join(html_paragraphs)


def generate_html_report(company_name: str, summary_card: str, detailed_report: str, generated_at: str) -> str:
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
  html_report = template.format(company_name=company_name,
                                industry_name=industry_name,
                                market_type=market_type,
                                summary_content=summary_html,
                                detailed_content=detailed_html,
                                generation_date=generation_date)

  return html_report
