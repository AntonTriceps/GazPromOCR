import json
import re

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from .config import LLM_MODEL_NAME, SYSTEM_PROMPT, USER_PROMPT


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


def build_extraction_prompt(ocr_text):
    return f"""
{USER_PROMPT}

OCR text:
\"\"\"
{ocr_text}
\"\"\"
""".strip()


def extract_json_with_llm(ocr_text, tokenizer, model, device):
    prompt = build_extraction_prompt(ocr_text)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
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

    match = re.search(r"\{.*\}", answer, flags=re.DOTALL)
    if not match:
        raise ValueError(f"LLM не вернула JSON:\n{answer}")

    return json.loads(match.group(0))