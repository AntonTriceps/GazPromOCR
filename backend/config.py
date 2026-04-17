LLM_MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
OCR_MODEL_NAME = "lightonai/LightOnOCR-2-1B"

SYSTEM_PROMPT = "Ты извлекаешь структурированные данные из OCR-текста и отвечаешь только JSON."
USER_PROMPT = """
Ты извлекаешь данные из OCR-текста документа.

Задача:
- Верни только валидный JSON
- Не придумывай значения
- Если поле не найдено, ставь null
- Числа нормализуй
- Не добавляй пояснений вне JSON

Нужная схема:
{{
  "document_type": null,
  "document_number": null,
  "sender": null,
  "receive_date": null,
  "pickup_address": null,
  "consignee": null,
  "completion_request_number": null,
  "preliminary_delivery_address": null,
  "spec_gk": null,
  "amount_rub": null,
  "receiver_fio": null,
  "phone": null,
  "items": []
}}
"""
