import requests
import json
import time

# 테스트 데이터 로드
with open('test_credit_rating_request.json', 'r', encoding='utf-8') as f:
  data = json.load(f)

print("API 요청 데이터:", json.dumps(data, ensure_ascii=False, indent=2))

# 비동기식 API 테스트 (환경 변수 오류 방지)
print("\n비동기식 API 테스트 시작...")
start_time = time.time()

try:
  # 1. 비동기 요청 제출
  response = requests.post("http://localhost:8000/v1/credit-rating/evaluate-async", json=data)

  print(f"요청 상태 코드: {response.status_code}")

  if response.status_code == 200:
    result = response.json()
    request_id = result.get("request_id")
    print(f"요청 ID: {request_id}")
    print(f"상태: {result.get('status')}")
    print(f"메시지: {result.get('message')}")

    # 2. 상태 확인 (5번 시도)
    if request_id:
      print("\n결과 폴링 시작...")
      for i in range(5):
        time.sleep(3)  # 3초 대기
        status_response = requests.get(f"http://localhost:8000/v1/credit-rating/status/{request_id}")

        status_result = status_response.json()
        print(f"\n폴링 {i+1}/5:")
        print(f"상태: {status_result.get('status')}")
        print(f"메시지: {status_result.get('message')}")

        if status_result.get('status') == "COMPLETED":
          print("\n결과:")
          print(json.dumps(status_result.get('result'), ensure_ascii=False, indent=2))
          break
  else:
    print(f"오류 응답: {response.text}")

  end_time = time.time()
  print(f"\n소요 시간: {end_time - start_time:.2f}초")

except Exception as e:
  print(f"오류 발생: {str(e)}")
