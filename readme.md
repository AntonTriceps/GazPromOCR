Эндпоинт OCR: api.py:30
POST /ocr/generate
Принимает PDF через multipart/form-data (поле file), запускает OCR и возвращает ocr_text.

Эндпоинт LLM JSON: api.py:66
POST /llm/generate-json
Принимает JSON с полем ocr_text, вызывает LLM и возвращает data (JSON-объект).

Запуск API из корня проекта:

1. Установить зависимости:
	pip install -r requirements.txt
2. Запустить сервер:
	uvicorn backend.api:app --reload

После старта Swagger будет доступен по адресу http://127.0.0.1:8000/docs

Запуск Frontend проекта:
1. Перейти в папку frontend:
	cd frontend
2. Установить зависимости:
   	npm install
3. Сделать запуск
   	npm run dev
