from __future__ import annotations

import io

import markdown as md
from docx import Document as DocxDocument
from pypdf import PdfReader

# Each extractor returns a list of (page_number, text) tuples so chunks can
# remember which page they came from (page 0 means "not paginated").


def extract_pdf(data: bytes) -> list[tuple[int, str]]:
    reader = PdfReader(io.BytesIO(data))
    pages: list[tuple[int, str]] = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append((i, text))
    return pages


def extract_docx(data: bytes) -> list[tuple[int, str]]:
    doc = DocxDocument(io.BytesIO(data))
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return [(0, text)] if text.strip() else []


def extract_markdown(data: bytes) -> list[tuple[int, str]]:
    raw = data.decode("utf-8", errors="ignore")
    # Strip markdown to roughly plain text for cleaner embeddings.
    html = md.markdown(raw)
    text = _strip_html(html)
    return [(0, text)] if text.strip() else []


def extract_text(data: bytes) -> list[tuple[int, str]]:
    text = data.decode("utf-8", errors="ignore")
    return [(0, text)] if text.strip() else []


def _strip_html(html: str) -> str:
    out = []
    in_tag = False
    for ch in html:
        if ch == "<":
            in_tag = True
        elif ch == ">":
            in_tag = False
        elif not in_tag:
            out.append(ch)
    return "".join(out)


def extract_document(filename: str, mime_type: str, data: bytes) -> list[tuple[int, str]]:
    name = filename.lower()
    if name.endswith(".pdf") or mime_type == "application/pdf":
        return extract_pdf(data)
    if name.endswith(".docx") or "wordprocessingml" in mime_type:
        return extract_docx(data)
    if name.endswith((".md", ".markdown")):
        return extract_markdown(data)
    # Fallback: treat everything else as plain text.
    return extract_text(data)
