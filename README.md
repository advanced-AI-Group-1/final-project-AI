# 금융 AI 분석 API

재무제표 데이터 검색 및 신용평가 보고서 생성을 위한 FastAPI 기반 AI 백엔드 서비스입니다.

## 주요 기능

1. **재무제표 데이터 검색 API**
   - 프롬프트를 받아 RAG(Retrieval Augmented Generation)를 통해 유사도가 높은 기업의 재무제표 데이터를 검색합니다.

2. **신용평가 등급 산출 API**
   - 재무제표 데이터를 기반으로 LLM(Large Language Model)을 사용하여 신용평가 등급을 산출합니다.

3. **보고서 생성 API**
   - 신용평가 결과와 재무제표 데이터를 기반으로 AI 에이전트를 통해 보고서를 생성합니다.

## 프로젝트 구조

프로젝트는 도메인 기반 폴더 구조로 구성되어 있습니다.

```
final-project-AI/
├── app/
│   ├── api/                     # API 엔드포인트 정의
│   │   ├── v1/                  # API 버전 관리
│   │   │   ├── financial_data.py
│   │   │   ├── credit_rating.py
│   │   │   └── report_generation.py
│   │   └── router.py            # API 라우터 설정
│   │
│   ├── core/                    # 핵심 설정 및 유틸리티
│   │   └── config.py            # 애플리케이션 설정
│   │
│   ├── domain/                  # 도메인 로직
│   │   ├── financial_data/      # 재무제표 데이터 도메인
│   │   │   └── service.py
│   │   ├── credit_rating/       # 신용평가 도메인
│   │   │   └── service.py
│   │   └── report_generation/   # 보고서 생성 도메인
│   │       └── service.py
│   │
│   └── infrastructure/          # 인프라 계층
│       ├── database/            # 데이터베이스 관련
│       │   └── connection.py
│       ├── models/              # 데이터 모델
│       │   └── financial_data.py
│       ├── vector_store/        # 벡터 저장소
│       │   └── repository.py
│       └── llm/                 # LLM 관련
│           └── manager.py
│
├── tests/                       # 테스트 코드
│   ├── unit/                    # 단위 테스트
│   └── integration/             # 통합 테스트
│
├── main.py                      # 애플리케이션 진입점
├── gunicorn_conf.py             # Gunicorn 설정 파일
├── run.py                       # 서버 실행 스크립트
├── requirements.txt             # 의존성 패키지 목록
└── README.md                    # 프로젝트 설명
```

각 폴더에는 `.gitkeep` 파일을 추가하여 빈 폴더도 Git에 포함되도록 했습니다.

## 설치 및 실행 방법

1. 의존성 패키지 설치
```bash
pip install -r requirements.txt
```

2. 환경 변수 설정
```bash
# .env 파일 생성
OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=sqlite+aiosqlite:///./data/finance_ai.db
RUNPOD_API_KEY=your_runpod_api_key
TAVILY_API_KEY=your_tavily_api_key  # 회사 정보 검색을 위한 Tavily API 키
```

3. 서버 실행 방법

### 개발 환경
```bash
uvicorn main:app --reload
```

### 프로덕션 환경 (Gunicorn + Uvicorn)
```bash
# Linux/Mac
gunicorn main:app -c gunicorn_conf.py

# 또는 스크립트 사용
python run.py

# Windows
start.bat
```

4. API 문서 접속
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 엔드포인트

### 재무제표 데이터 검색 API
- `POST /v1/financial-data/search`
  - 프롬프트를 통해 유사한 재무제표 데이터 검색

### 신용평가 등급 산출 API
- `POST /v1/credit-rating/evaluate`
  - 재무제표 데이터를 기반으로 신용평가 등급 산출

### 보고서 생성 API
- `POST /v1/report/generate`
  - 신용평가 결과와 재무제표 데이터를 기반으로 보고서 생성
