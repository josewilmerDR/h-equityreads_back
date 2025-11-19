# services/books.py
import json
from pathlib import Path
from typing import List, Optional, Dict, Any

from flask import Blueprint, jsonify, abort

# Creamos un Blueprint para agrupar todas las rutas de libros
books_bp = Blueprint("books", __name__, url_prefix="/api/books")

# ======================
# Directorios del backend
# ======================

# /backend/services/books.py → parent = /backend/services
# parent.parent = /backend
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
BOOKS_DIR = DATA_DIR / "books"


# ======================
# Helpers
# ======================

def load_book_meta(book_id: str) -> Optional[Dict[str, Any]]:
    """Carga el meta.json de un libro."""
    meta_path = BOOKS_DIR / book_id / "meta.json"
    if not meta_path.exists():
        return None

    with meta_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_all_books_meta() -> List[Dict[str, Any]]:
    """Devuelve la lista de todos los libros (solo metadatos para catálogo)."""
    books = []

    if not BOOKS_DIR.exists():
        return books

    for book_folder in sorted(BOOKS_DIR.iterdir()):
        if not book_folder.is_dir():
            continue

        meta_path = book_folder / "meta.json"
        if not meta_path.exists():
            continue

        with meta_path.open("r", encoding="utf-8") as f:
            meta = json.load(f)

        books.append({
            "id": meta.get("id"),
            "title": meta.get("title"),
            "author": meta.get("author"),
            "description": meta.get("description", ""),
            "coverUrl": meta.get("coverUrl", ""),
            "chaptersCount": meta.get("chaptersCount", 0),
        })

    return books


def load_chapter(book_id: str, number: int) -> Optional[Dict[str, Any]]:
    """Carga el contenido HTML de un capítulo."""
    meta = load_book_meta(book_id)
    if not meta:
        return None

    # Buscar título de capítulo si está en el meta.json
    chapter_title = None
    for ch in meta.get("chapters", []):
        if ch.get("number") == number:
            chapter_title = ch.get("title")
            break

    chapter_path = BOOKS_DIR / book_id / "chapters" / f"{number}.html"
    if not chapter_path.exists():
        return None

    with chapter_path.open("r", encoding="utf-8") as f:
        content_html = f.read()

    return {
        "bookId": book_id,
        "number": number,
        "title": chapter_title or f"Capítulo {number}",
        "contentHtml": content_html,
    }


# ======================
# Endpoints del Blueprint
# ======================

@books_bp.get("")
def get_books():
    """GET /api/books → lista de libros."""
    return jsonify(load_all_books_meta())


@books_bp.get("/<book_id>")
def get_book(book_id: str):
    """GET /api/books/<book_id> → detalle del libro."""
    meta = load_book_meta(book_id)
    if not meta:
        abort(404, description="Libro no encontrado")

    return jsonify(meta)


@books_bp.get("/<book_id>/chapters/<int:number>")
def get_book_chapter(book_id: str, number: int):
    """GET /api/books/<id>/chapters/<n> → contenido de capítulo."""
    chapter = load_chapter(book_id, number)
    if not chapter:
        abort(404, description="Capítulo no encontrado")

    return jsonify(chapter)
