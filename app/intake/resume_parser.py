"""履歷檔案攝取：PDF / DOCX / 純文字 → 純文字。"""
from __future__ import annotations

from io import BytesIO


def extract_text(data: bytes, filename: str) -> str:
    """依副檔名抽取純文字；未知副檔名以 UTF-8 文字處理。"""
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return _extract_pdf(data)
    if name.endswith(".docx"):
        return _extract_docx(data)
    return data.decode("utf-8", errors="ignore")


def _extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data))
    parts = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(parts).strip()


def _extract_docx(data: bytes) -> str:
    from docx import Document

    doc = Document(BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs).strip()
