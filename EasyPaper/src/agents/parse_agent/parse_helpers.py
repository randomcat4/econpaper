"""
Helper utilities for ParseAgent.
"""
from __future__ import annotations

from typing import IO

MAX_TEXT_CHARS = 48_000


def extract_pdf_text(path: str) -> str:
    """
    Extract text from a PDF using PyMuPDF.
    """
    import fitz

    doc = fitz.open(path)
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    text = "\n\n".join(pages)
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS] + "\n... [truncated]"
    return text


def extract_bytes_text(content: IO[bytes]) -> str:
    """
    Extract text from in-memory PDF bytes using PyMuPDF.
    """
    import fitz

    raw = content.read() if hasattr(content, "read") else content
    doc = fitz.open(stream=raw, filetype="pdf")
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    text = "\n\n".join(pages)
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS] + "\n... [truncated]"
    return text
