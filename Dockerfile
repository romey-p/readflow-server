FROM python:3.12-slim

WORKDIR /workspace

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY requirements-docker.txt .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -r requirements-docker.txt \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    --index-strategy unsafe-best-match

COPY app/core/config.py ./app/core/config.py
COPY app/ml/ ./app/ml/
COPY app/schemas/analysis_schema.py ./app/schemas/analysis_schema.py
COPY app/services/analysis_service.py ./app/services/analysis_service.py
COPY app/routers/analysis_router.py ./app/routers/analysis_router.py
COPY app/main.py ./app/main.py

COPY weights/ ./weights/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]