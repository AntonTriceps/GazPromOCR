import gc
import json
import torch

from ocr import load_ocr_model, extract_text_from_scanned_pdf
from llm import load_llm, extract_json_with_llm


def unload_torch_model(*objects):
    for obj in objects:
        try:
            del obj
        except Exception:
            pass

    gc.collect()

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()


def run_pipeline(pdf_path: str) -> dict:
    # 1. OCR
    ocr_processor, ocr_model, ocr_device, ocr_dtype = load_ocr_model()
    ocr_text = extract_text_from_scanned_pdf(
        pdf_path,
        ocr_processor,
        ocr_model,
        ocr_device,
        ocr_dtype,
    )

    # 2. выгрузка OCR
    unload_torch_model(ocr_model, ocr_processor)

    # 3. LLM
    llm_tokenizer, llm_model, llm_device = load_llm()
    result = extract_json_with_llm(
        ocr_text,
        llm_tokenizer,
        llm_model,
        llm_device,
    )

    # 4. выгрузка LLM
    unload_torch_model(llm_model, llm_tokenizer)

    return {
        "ocr_text": ocr_text,
        "json": result,
    }


if __name__ == "__main__":
    pdf_path = ".files/passp5.pdf"
    result = run_pipeline(pdf_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))