import re

from apps.ai_search.models import ResourceChunk


PAGE_MARKER_RE = re.compile(
    r"^\s*---\s*Page\s+(\d+)\s*---\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def parse_ocr_pages(extracted_text: str) -> list[tuple[int, str]]:
    if not extracted_text:
        return []

    matches = list(PAGE_MARKER_RE.finditer(extracted_text))

    if not matches:
        text = extracted_text.strip()
        return [(1, text)] if text else []

    pages = []

    for index, match in enumerate(matches):
        page_number = int(match.group(1))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(extracted_text)

        content = extracted_text[start:end].strip()

        if content:
            pages.append((page_number, content))

    return pages


def split_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if overlap < 0:
        raise ValueError("overlap cannot be negative")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - overlap

    return chunks


def build_resource_chunks(
    resource_file,
    ocr_job,
    *,
    chunk_size: int = 1200,
    overlap: int = 200,
) -> list[ResourceChunk]:
    pages = parse_ocr_pages(ocr_job.extracted_text)

    chunks = []

    for page_number, page_content in pages:
        page_chunks = split_text(
            page_content,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        for chunk_index, content in enumerate(page_chunks):
            chunks.append(
                ResourceChunk(
                    resource_file=resource_file,
                    ocr_job=ocr_job,
                    page_number=page_number,
                    chunk_index=chunk_index,
                    content=content,
                )
            )


    
    return chunks
