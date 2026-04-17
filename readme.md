Эндпоинт OCR: api.py:30
POST /ocr/generate
Принимает PDF через multipart/form-data (поле file), запускает OCR и возвращает ocr_text.

Эндпоинт LLM JSON: api.py:66
POST /llm/generate-json
Принимает JSON с полем ocr_text, вызывает LLM и возвращает data (JSON-объект).