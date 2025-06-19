#!/usr/bin/env python
"""
FastAPI 애플리케이션을 Gunicorn으로 실행하기 위한 스크립트
"""
import os
import subprocess
import sys


def run_server():
  """
    Gunicorn 서버를 실행합니다.
    """
  # 환경 변수 설정 (필요한 경우)
  os.environ.setdefault("ENV", "production")

  # Gunicorn 명령어 구성
  cmd = [
      "gunicorn",
      "main:app",
      "-c",
      "gunicorn_conf.py",
  ]

  # 디버그 모드인 경우 리로드 옵션 추가
  if os.environ.get("DEBUG", "").lower() in ("true", "1", "t"):
    cmd.append("--reload")

  # 명령어 실행
  subprocess.run(cmd)


if __name__ == "__main__":
  run_server()
