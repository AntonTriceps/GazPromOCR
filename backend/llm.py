import json
import re
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


LLM_MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"


def load_llm():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if device == "cuda" else torch.float32

    tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(
        LLM_MODEL_NAME,
        torch_dtype=dtype,
    ).to(device)

    model.eval()
    return tokenizer, model, device


def build_extraction_prompt(ocr_text: str) -> str:
    return f"""
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

OCR text:
\"\"\"
{ocr_text}
\"\"\"
""".strip()


def extract_json_with_llm(ocr_text: str, tokenizer, model, device) -> dict:
    prompt = build_extraction_prompt(ocr_text)

    messages = [
        {"role": "system", "content": "Ты извлекаешь структурированные данные из OCR-текста и отвечаешь только JSON."},
        {"role": "user", "content": prompt},
    ]

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = tokenizer(text, return_tensors="pt").to(device)

    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens=1024,
            do_sample=False,
        )

    generated = outputs[0][inputs.input_ids.shape[1]:]
    answer = tokenizer.decode(generated, skip_special_tokens=True).strip()

    # попытка вытащить JSON из ответа
    match = re.search(r"\{.*\}", answer, flags=re.DOTALL)
    if not match:
        raise ValueError(f"LLM не вернула JSON:\n{answer}")

    return json.loads(match.group(0))