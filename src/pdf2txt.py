import pathlib
import sys

import pymupdf  # pip install pymupdf


def pdf_to_text(pdf_path, out_path=None, page_marks=True):
    """Extract text from a PDF. Returns the text; also writes it next to the PDF."""
    pdf_path = pathlib.Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    chunks, skipped = [], []
    with pymupdf.open(pdf_path) as doc:
        for page in doc:
            text = page.get_text("text").strip()
            if not text:
                skipped.append(page.number + 1)   # image-only page
                continue
            if page_marks:
                text = f"--- page {page.number + 1} ---\n{text}"
            chunks.append(text)

    result = "\n\n".join(chunks)
    out = pathlib.Path(out_path) if out_path else pdf_path.with_suffix(".txt")
    out.write_text(result, encoding="utf-8")

    if skipped:
        print(f"skipped {len(skipped)} image-only page(s): {skipped}", file=sys.stderr)
    print(f"wrote {out} ({len(result)} chars)", file=sys.stderr)
    return result


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "text.pdf"
    pdf_to_text(target)