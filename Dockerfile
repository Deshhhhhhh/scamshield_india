# ---------- build stage: wheelhouse ----------
FROM python:3.15-slim AS build
WORKDIR /wheels
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ---------- runtime stage ----------
FROM python:3.15-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

RUN groupadd -r scamshield && useradd -r -g scamshield -u 10001 scamshield
WORKDIR /app

COPY --from=build /wheels /tmp/wheels
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --no-index --find-links=/tmp/wheels -r /tmp/requirements.txt \
    && rm -rf /tmp/wheels /tmp/requirements.txt

# source
COPY scamshield ./scamshield
COPY data/scripts ./data/scripts
COPY data/golden ./data/golden
COPY dashboard ./dashboard
COPY bot ./bot
COPY scripts ./scripts
COPY landing ./landing

# train the baseline model inside the image (hand seeds + synthetic templates; no network)
RUN python data/scripts/build_dataset.py \
    && python -m scamshield.model --csv data/training/train.csv \
    && mkdir -p /app/data/logs && chown -R scamshield:scamshield /app

USER scamshield
EXPOSE 8000 8501

HEALTHCHECK --interval=30s --timeout=4s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/v1/health', timeout=3).status==200 else 1)"

CMD ["python", "-m", "uvicorn", "scamshield.main:app", "--host", "0.0.0.0", "--port", "8000"]
