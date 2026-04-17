from pathlib import Path
import torch
import pypdfium2 as pdfium
from transformers import LightOnOcrForConditionalGeneration, LightOnOcrProcessor
from config import OCR_MODEL_NAME


def load_ocr_model():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if device == "cuda" else torch.float32

    processor = LightOnOcrProcessor.from_pretrained(OCR_MODEL_NAME)
    model = LightOnOcrForConditionalGeneration.from_pretrained(
        OCR_MODEL_NAME,
        torch_dtype=dtype,
    ).to(device)

    model.eval()
    return processor, model, device, dtype


def extract_text_from_scanned_pdf(pdf_path, processor, model, device, dtype):
    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {pdf_path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Ожидается PDF файл")

    pdf = pdfium.PdfDocument(str(path))
    page_texts = []

    for i in range(len(pdf)):
        page = pdf[i]
        image = page.render(scale=2.77).to_pil().convert("RGB")

        conversation = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                ],
            }
        ]

        inputs = processor.apply_chat_template(
            conversation,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )

        inputs = {
            k: v.to(device=device, dtype=dtype) if v.is_floating_point() else v.to(device)
            for k, v in inputs.items()
        }

        with torch.inference_mode():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=1024,
            )

        generated_ids = output_ids[0, inputs["input_ids"].shape[1]:]
        text = processor.decode(generated_ids, skip_special_tokens=True).strip()

        if text:
            page_texts.append(text)

    return "\n\n".join(page_texts)