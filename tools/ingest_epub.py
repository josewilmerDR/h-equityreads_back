import os
import json
import shutil
import warnings
from pathlib import Path
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BOOKS_DIR = DATA_DIR / "books"

def get_epub_cover(book, output_dir: Path) -> str:
    # ... (Misma lógica de portada) ...
    cover_item = None
    if book.get_metadata('OPF', 'cover'):
        try:
            cover_id = book.get_metadata('OPF', 'cover')[0][1]
            cover_item = book.get_item_with_id(cover_id)
        except: pass
    
    if not cover_item:
        for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
            if 'cover' in item.get_name().lower():
                cover_item = item
                break

    if cover_item:
        file_name = cover_item.get_name().split('/')[-1]
        cover_path = output_dir / file_name
        with open(cover_path, 'wb') as f:
            f.write(cover_item.get_content())
        return f"/cover/{file_name}"
    return ""

def process_epub(epub_path: Path):
    if not epub_path.exists():
        return

    print(f"--- Procesando: {epub_path.name} ---")
    
    try:
        book = epub.read_epub(str(epub_path))
    except Exception as e:
        print(f"Error leyendo EPUB: {e}")
        return

    # Metadatos
    title = book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else "Sin Título"
    author = book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else "Desconocido"
    
    # Crear ID y carpetas
    book_slug = epub_path.stem.lower().replace(' ', '-').replace('_', '-')
    book_dir = BOOKS_DIR / book_slug
    
    if book_dir.exists():
        shutil.rmtree(book_dir)
    book_dir.mkdir(parents=True, exist_ok=True)

    # --- CRÍTICO: Copiar el .epub original a la carpeta ---
    shutil.copy(epub_path, book_dir / "book.epub")
    print(f"   [+] EPUB original copiado.")

    # Extraer Portada
    cover_url = get_epub_cover(book, book_dir)

    # Generar meta.json simple
    meta = {
        "id": book_slug,
        "title": title,
        "author": author,
        "description": "Importado automáticamente",
        "coverUrl": cover_url,
        "epubUrl": f"/api/books/{book_slug}/download", # URL para el frontend
        "source": "local"
    }

    with open(book_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"--- Completado: {title} ---")


if __name__ == "__main__":
    source_docs = DATA_DIR / "source_docs"
    # Procesamos todo lo que haya en source_docs
    epubs = list(source_docs.glob("*.epub"))
    for epub_file in epubs:
        process_epub(epub_file)
