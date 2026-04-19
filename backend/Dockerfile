FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PIP_NO_CACHE_DIR=1 \
	HF_HOME=/cache/huggingface \
	TRANSFORMERS_CACHE=/cache/huggingface/transformers \
	TORCH_HOME=/cache/torch

WORKDIR /app

RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
	   ca-certificates \
	   libgomp1 \
	&& rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN python -m pip install --upgrade pip \
	&& python -m pip install --extra-index-url https://download.pytorch.org/whl/cu130 -r requirements.txt

COPY backend ./backend

EXPOSE 8000

CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
