import requests
import json
import time

# 서버 URL
BASE_URL = "http://localhost:8000"

# 1. 벡터 DB 초기화 API 호출
print("1. 벡터 DB 초기화 API 호출 중...")
init_response = requests.post(f"{BASE_URL}/v1/financial-data/initialize-vector-store")
print(f"상태 코드: {init_response.status_code}")
print(f"응답 내용: {json.dumps(init_response.json(), ensure_ascii=False, indent=2)}")
print("-" * 50)

# 벡터 DB 초기화가 완료될 때까지 잠시 대기
if init_response.status_code == 200:
  print("벡터 DB 초기화 중... 10초 대기")
  time.sleep(10)

# 2. 신용등급 평가 API 호출
print("\n2. 신용등급 평가 API 호출 중...")

# 테스트 데이터 로드
with open('test_credit_rating_request.json', 'r', encoding='utf-8') as f:
  data = json.load(f)

print("요청 데이터:")
print(json.dumps(data, ensure_ascii=False, indent=2))

# 신용등급 평가 API 호출
try:
  credit_response = requests.post(f"{BASE_URL}/v1/credit-rating/evaluate", json=data)
  print(f"상태 코드: {credit_response.status_code}")

  if credit_response.status_code == 200:
    result = credit_response.json()
    print("\n신용등급 평가 결과:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
  else:
    print(f"오류 응답: {credit_response.text}")
except Exception as e:
  print(f"API 호출 중 오류 발생: {str(e)}")

print("\n테스트 완료!")
