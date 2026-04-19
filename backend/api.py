from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import pypdfium2 as pdfium
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .database import (
    add_entry,
    create_cabinet,
    delete_cabinet,
    delete_entry,
    get_device_card,
    list_cabinets,
    list_device_cards,
    list_entries,
    save_device_card,
)
from .llm import extract_json_with_llm, load_llm
from .ocr import extract_text_from_scanned_pdf, load_ocr_model
from .pipeline import unload_torch_model


# ---------------------------------------------------------------------------
#  Request / Response models
# ---------------------------------------------------------------------------

class LlmJsonRequest(BaseModel):
    ocr_text: str = Field(..., min_length=1, description="OCR-текст для извлечения JSON")


class OcrResponse(BaseModel):
    ocr_text: str
    page_count: int = 0


class LlmJsonResponse(BaseModel):
    data: dict[str, Any]


class CabinetCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Название шкафа")


class CabinetEntryCreateRequest(BaseModel):
    document_name: str = ""
    serial_number: str = ""
    pages: str = ""
    certificate: str = ""


class DeviceCardCreateRequest(BaseModel):
    entry_id: int | None = None
    name: str = ""
    serial_number: str = ""
    decimal_number: str = ""
    production_date: str = ""
    warranty_period: str = ""
    raw_json: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
#  App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="GazPromOCR API",
    description="API для OCR и генерации структурированного JSON через LLM",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
#  OCR & LLM endpoints (existing, updated)
# ---------------------------------------------------------------------------

@app.post("/ocr/generate", response_model=OcrResponse)
async def generate_ocr(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Нужно передать PDF-файл")

    suffix = Path(file.filename).suffix or ".pdf"
    temp_path = None

    try:
        with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(await file.read())
            temp_path = temp_file.name

        # Считаем количество страниц PDF
        page_count = 0
        try:
            with pdfium.PdfDocument(temp_path) as pdf_doc:
                page_count = len(pdf_doc)
        except Exception:
            pass

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

        return OcrResponse(ocr_text=ocr_text, page_count=page_count)

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


# ---------------------------------------------------------------------------
#  Cabinet endpoints
# ---------------------------------------------------------------------------

@app.get("/cabinets")
def api_list_cabinets():
    return list_cabinets()


@app.post("/cabinets", status_code=201)
def api_create_cabinet(payload: CabinetCreateRequest):
    try:
        return create_cabinet(payload.name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Не удалось создать шкаф: {exc}") from exc


@app.delete("/cabinets/{cabinet_id}")
def api_delete_cabinet(cabinet_id: int):
    if not delete_cabinet(cabinet_id):
        raise HTTPException(status_code=404, detail="Шкаф не найден")
    return {"ok": True}


@app.get("/cabinets/{cabinet_id}/entries")
def api_list_entries(cabinet_id: int):
    return list_entries(cabinet_id)


@app.post("/cabinets/{cabinet_id}/entries", status_code=201)
def api_add_entry(cabinet_id: int, payload: CabinetEntryCreateRequest):
    try:
        return add_entry(
            cabinet_id=cabinet_id,
            document_name=payload.document_name,
            serial_number=payload.serial_number,
            pages=payload.pages,
            certificate=payload.certificate,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Не удалось добавить запись: {exc}") from exc


@app.delete("/cabinets/{cabinet_id}/entries/{entry_id}")
def api_delete_entry(cabinet_id: int, entry_id: int):
    if not delete_entry(entry_id):
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return {"ok": True}


# ---------------------------------------------------------------------------
#  Device card endpoints
# ---------------------------------------------------------------------------

@app.get("/cards")
def api_list_cards():
    return list_device_cards()


@app.get("/cards/{card_id}")
def api_get_card(card_id: int):
    card = get_device_card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Карточка не найдена")
    return card


@app.post("/cards", status_code=201)
def api_save_card(payload: DeviceCardCreateRequest):
    try:
        return save_device_card(
            name=payload.name,
            serial_number=payload.serial_number,
            decimal_number=payload.decimal_number,
            production_date=payload.production_date,
            warranty_period=payload.warranty_period,
            raw_json=payload.raw_json,
            entry_id=payload.entry_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Не удалось сохранить карточку: {exc}") from exc