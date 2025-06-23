from fastapi import APIRouter
from app.api.v1.financial_data import router as financial_data_router
from app.api.v1.credit_rating import router as credit_rating_router
from app.api.v1.report_generation import router as report_generation_router

api_router = APIRouter()

# API 버전 관리를 위한 prefix 설정
api_router.include_router(financial_data_router, prefix="/api/ai/v1/financial-data", tags=["재무제표 데이터"])
api_router.include_router(credit_rating_router, prefix="/api/ai/v1/credit-rating", tags=["신용평가"])
api_router.include_router(report_generation_router, prefix="/api/ai/v1/report", tags=["보고서 생성"])
