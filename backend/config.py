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

#USER_PROMPT = """
# Ты — система извлечения структурированных данных из OCR-текста технических документов.

# Твоя задача:
# 1. Проанализировать OCR-текст документа.
# 2. Извлечь только фактически найденные данные.
# 3. Вернуть только валидный JSON.
# 4. Не добавлять никаких пояснений, комментариев, markdown, поясняющего текста до или после JSON.

# Жёсткие правила:
# - Не придумывай значения.
# - Не восстанавливай данные "по смыслу", если они явно не присутствуют в тексте.
# - Если поле не найдено, не включай его в JSON вообще.
# - Не используй null.
# - Не используй пустые строки.
# - Не используй пустые массивы.
# - Не используй пустые объекты.
# - Не добавляй поля, которых нет в схеме.
# - Если значение неоднозначно, лучше не добавлять поле.
# - Если документ содержит несколько единиц оборудования, используй массив items или serial_numbers.
# - Если документ содержит перечень документации, используй массив documents.
# - Если документ содержит технические характеристики в виде таблицы или списка, используй массив technical_specifications.
# - Сохраняй оригинальные формулировки максимально близко к тексту, кроме явной нормализации OCR-ошибок.
# - Даты по возможности приводи к формату YYYY-MM-DD.
# - Если у даты есть время, используй формат YYYY-MM-DD HH:MM:SS.
# - Числа по возможности нормализуй:
#   - "2 668 888,02" -> 2668888.02
#   - "15" -> 15
# - Если тип документа нельзя определить точно, используй "unknown".

# Определи document_type из одного из значений:
# - "equipment_passport"
# - "group_passport"
# - "acceptance_certificate"
# - "document_list"
# - "shipping_note"
# - "invoice"
# - "unknown"

# Используй следующую схему JSON.
# Включай только найденные поля.

# {
#   "document_type": "string",

#   "meta": {
#     "title": "string",
#     "document_number": "string",
#     "document_code": "string",
#     "date": "string",
#     "version": "string",
#     "source_file": "string"
#   },

#   "product": {
#     "name": "string",
#     "model": "string",
#     "type": "string",
#     "code": "string",
#     "serial_number": "string",
#     "serial_numbers": ["string"],
#     "inventory_number": "string",
#     "passport_number": "string",
#     "manufacturer": "string",
#     "description": "string"
#   },

#   "manufacturer": {
#     "name": "string",
#     "address": "string",
#     "phone": "string",
#     "email": "string",
#     "website": "string"
#   },

#   "acceptance": {
#     "status": "string",
#     "date": "string",
#     "inspector": "string",
#     "organization": "string",
#     "stamp_present": true
#   },

#   "logistics": {
#     "sender": "string",
#     "consignee": "string",
#     "pickup_address": "string",
#     "delivery_address": "string",
#     "preliminary_delivery_address": "string",
#     "places_count": 0,
#     "gross_weight_kg": 0,
#     "packaging": "string"
#   },

#   "technical_specifications": [
#     {
#       "name": "string",
#       "value": "string",
#       "unit": "string"
#     }
#   ],

#   "completeness": [
#     {
#       "name": "string",
#       "code": "string",
#       "quantity": 0,
#       "unit": "string",
#       "comment": "string"
#     }
#   ],

#   "items": [
#     {
#       "line_no": 0,
#       "code": "string",
#       "name": "string",
#       "model": "string",
#       "type": "string",
#       "characteristics": "string",
#       "serial_number": "string",
#       "quantity": 0,
#       "actual_quantity": 0,
#       "unit": "string"
#     }
#   ],

#   "documents": [
#     {
#       "line_no": 0,
#       "name": "string",
#       "document_number": "string",
#       "serial_number": "string",
#       "pages": "string",
#       "certificate": "string"
#     }
#   ],

#   "commercial": {
#     "specification_number": "string",
#     "specification_date": "string",
#     "contract_number": "string",
#     "contract_date": "string",
#     "request_number": "string",
#     "amount_rub": 0
#   },

#   "contacts": {
#     "person": "string",
#     "phone": "string"
#   },

#   "additional": {
#     "notes": "string",
#     "raw_text_excerpt": "string"
#   }
# }

# Требования к ответу:
# - Ответ должен быть только JSON.
# - Без markdown.
# - Без тройных кавычек.
# - Без пояснений.
# - Без комментариев.
# - Без null.
# - Без полей с пустыми значениями.
#"""
