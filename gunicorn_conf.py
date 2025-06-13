import multiprocessing
import os

# Gunicorn 설정
bind = os.getenv("BIND", "0.0.0.0:8000")
workers = int(os.getenv("WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
keepalive = 120
timeout = 120
graceful_timeout = 30
max_requests = 1000
max_requests_jitter = 50
accesslog = "-"
errorlog = "-"
loglevel = "info"

# 환경 변수에서 추가 설정 가져오기
reload = os.getenv("RELOAD", "false").lower() in ("true", "1", "t")
preload_app = os.getenv("PRELOAD_APP", "false").lower() in ("true", "1", "t")

# SSL 설정 (필요한 경우)
certfile = os.getenv("CERTFILE", None)
keyfile = os.getenv("KEYFILE", None)

# 프로세스 이름
proc_name = "finance-ai-backend"

# 워커 임시 디렉토리
worker_tmp_dir = "/tmp"

# 로그 형식
logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "gunicorn.error": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "gunicorn.access": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}
