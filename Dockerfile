# Базовый образ: маленький Linux с уже установленным Python
FROM python:3.12-slim

# Не создавать .pyc-файлы и сразу выводить логи (без буферизации)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Сначала только зависимости: Docker закэширует этот слой,
# и при изменении кода библиотеки не будут ставиться заново
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Потом сам код
COPY main.py schemas.py store.py ./

# Запуск не от root (принцип минимальных прав)
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# Docker сам будет опрашивать /health и помечать контейнер healthy/unhealthy
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)" || exit 1

# 0.0.0.0 обязательно: иначе сервер будет недоступен снаружи контейнера
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
