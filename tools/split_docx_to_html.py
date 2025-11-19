import re
from pathlib import Path
from docx import Document

# ========= CONFIG =========

BOOK_ID = "orgullo-y-prejuicio-austen"

BASE_DIR = Path(__file__).resolve().parent.parent   # /backend
DOCX_PATH = BASE_DIR / "data" / "source_docs" / "Orgullo_y_Prejuicio_251118.docx"
CHAPTERS_DIR = BASE_DIR / "data" / "books" / BOOK_ID / "chapters"

CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)

# Regex para "CAPÍTULO I", "CAPITULO 1", "CAPÍTULO II TÍTULO..."
chapter_regex = re.compile(r"^CAP[ÍI]TULO\s+([0-9]+|[IVXLCDM]+)(.*)$", re.IGNORECASE)

romans = {
    'I': 1, 'V': 5, 'X': 10, 'L': 50,
    'C': 100, 'D': 500, 'M': 1000
}

def roman_to_int(s: str) -> int:
    total = 0
    prev = 0
    s = s.upper()
    for ch in reversed(s):
        value = romans.get(ch, 0)
        if value < prev:
            total -= value
        else:
            total += value
        prev = value
    return total


def save_chapter(number: int, title: str, paragraphs: list[str]):
    if not paragraphs:
        return

    title_suffix = f": {title}" if title else ""
    html_parts = [f"<h2>Capítulo {number}{title_suffix}</h2>"]
    html_parts += [f"<p>{p}</p>" for p in paragraphs]

    html = "\n".join(html_parts)
    out_path = CHAPTERS_DIR / f"{number}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Guardado capítulo {number} en {out_path}")


def main():
    doc = Document(DOCX_PATH)

    chapter_num = 0
    chapter_title = ""
    current_paragraphs: list[str] = []

    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue

        match = chapter_regex.match(text)
        if match:
            # Cerramos capítulo anterior
            if chapter_num > 0:
                save_chapter(chapter_num, chapter_title, current_paragraphs)

            raw_num = match.group(1).strip()
            title_part = match.group(2).strip()

            if raw_num.isdigit():
                chapter_num = int(raw_num)
            else:
                chapter_num = roman_to_int(raw_num)

            chapter_title = title_part or ""
            current_paragraphs = []
        else:
            current_paragraphs.append(text)

    # Guardar último capítulo
    if chapter_num > 0 and current_paragraphs:
        save_chapter(chapter_num, chapter_title, current_paragraphs)


if __name__ == "__main__":
    main()