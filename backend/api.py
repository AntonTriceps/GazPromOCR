from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .llm import extract_json_with_llm, load_llm
from .ocr import extract_text_from_scanned_pdf, load_ocr_model
from .pipeline import unload_torch_model


class LlmJsonRequest(BaseModel):
    ocr_text: str = Field(..., min_length=1, description="OCR-текст для извлечения JSON")


class OcrResponse(BaseModel):
    ocr_text: str


class LlmJsonResponse(BaseModel):
    data: dict[str, Any]


app = FastAPI(
    title="GazPromOCR API",
    description="API для OCR и генерации структурированного JSON через LLM",
    version="1.0.0",
)


@app.post("/ocr/generate", response_model=OcrResponse)
async def generate_ocr(request: Request):
    pdf_bytes = await request.body()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Нужно передать PDF-файл в теле запроса")

    suffix = ".pdf"
    temp_path = None

    try:
        with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(pdf_bytes)
            temp_path = temp_file.name

        ocr_processor, ocr_model, ocr_device, ocr_dtype = load_ocr_model()
        try:
            ocr_text = extract_text_from_scanned_pdf(
                temp_path,
                ocr_processor,
                ocr_model,
                ocr_device,
                ocr_dtype,
            )
        finally:
            unload_torch_model(ocr_model, ocr_processor)

        return OcrResponse(ocr_text=ocr_text)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ошибка OCR: {exc}") from exc
    finally:
        if temp_path:
            path = Path(temp_path)
            if path.exists():
                path.unlink()


@app.post("/llm/generate-json", response_model=LlmJsonResponse)
def generate_json_with_llm(payload: LlmJsonRequest):
    try:
        llm_tokenizer, llm_model, llm_device = load_llm()
        try:
            result = extract_json_with_llm(
                payload.ocr_text,
                llm_tokenizer,
                llm_model,
                llm_device,
            )
        finally:
            unload_torch_model(llm_model, llm_tokenizer)

        return LlmJsonResponse(data=result)

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ошибка LLM: {exc}") from exc