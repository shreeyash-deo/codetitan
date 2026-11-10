import os
from pathlib import Path
from typing import Optional


def extract_text_from_pdf(file_path: str) -> str:
    """Extract clean text from a PDF file using PyMuPDF (fitz) with page markers."""
    import fitz

    extracted_pages = []
    doc = fitz.open(file_path)
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").strip()
            if text:
                extracted_pages.append(f"--- Page {page_num + 1} ---\n{text}")
    finally:
        doc.close()

    return "\n\n".join(extracted_pages).strip()


def extract_text_from_docx(file_path: str) -> str:
    """Extract clean text from a DOCX file using python-docx."""
    from docx import Document

    doc = Document(file_path)
    paragraphs = []

    # Extract standard paragraphs
    for p in doc.paragraphs:
        text = p.text.strip()
        if text:
            paragraphs.append(text)

    # Extract any tabular data in the document
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                paragraphs.append(row_text)

    return "\n\n".join(paragraphs).strip()


def extract_text_from_txt(file_path: str) -> str:
    """Extract text from a plain text file with encoding fallback."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="latin-1", errors="replace") as f:
            return f.read().strip()


def extract_document_text(file_path: str, extension: str) -> str:
    """
    Unified text extraction dispatcher supporting PDF, DOCX, and TXT formats.
    """
    ext = extension.lower().lstrip(".")
    if ext == "pdf":
        return extract_text_from_pdf(file_path)
    elif ext in ("docx", "doc"):
        return extract_text_from_docx(file_path)
    elif ext == "txt":
        return extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file format for text extraction: .{ext}")
