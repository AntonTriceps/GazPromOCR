# GazPromOCR

## Краткое описание

GazPromOCR — сервис для обработки сканов технических паспортов PDF.

Что делает приложение:
- загружает PDF и при необходимости позволяет предварительно отредактировать страницы (поворот, нарезка);
- выполняет OCR распознавание текста по страницам;
- извлекает структурированные поля через локальную LLM в JSON;
- сохраняет данные в карточки устройств и шкафы;
- выгружает результат в JSON и Excel.

Архитектура:
- backend: FastAPI API для OCR, LLM, хранения карточек и работы со шкафами;
- frontend: Vue 3 интерфейс для загрузки PDF, просмотра результата и управления данными.

## Как запустить

### Вариант 1. Через Docker
1. Перейдите в корень проекта.
2. Запустите сборку и старт сервисов:

```bash
docker compose up --build
```

3. Откройте приложение:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000


### Вариант 2. Локальный запуск без Docker

Backend:

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
uvicorn backend.api:app --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Что использовалось

Backend:
- Python 3.11
- FastAPI, Uvicorn
- PyTorch
- Transformers, Hugging Face Hub
- LightOnOCR-2-1B для OCR
- Qwen2.5-1.5B-Instruct для извлечения структурированных данных
- pypdfium2 для рендера страниц PDF

Frontend:
- Vue 3
- Vite
- vue-pdf-embed
- pdf-lib
- xlsx

Инфраструктура:
- Docker, Docker Compose
- кэш моделей через volume для Hugging Face и Torch

## Минимальные технические требования
- VRAM >= 8 ГБ
- 5 ГБ свободного места на накопителе
