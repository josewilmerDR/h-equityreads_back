# services/books.py
import os
import json
import tempfile
import pypandoc
from pathlib import Path
from typing import List, Optional, Dict, Any

from flask import Blueprint, jsonify, abort, request, send_from_directory
from werkzeug.utils import secure_filename
from firebase_admin import storage, firestore

books_bp = Blueprint("books", __name__, url_prefix="/api/books")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BOOKS_DIR = DATA_DIR / "books"

# ======================
# Helpers
# ======================

def load_book_meta(book_id: str) -> Optional[Dict[str, Any]]:
    meta_path = BOOKS_DIR / book_id / "meta.json"
    if not meta_path.exists():
        return None
    with meta_path.open("r", encoding="utf-8") as f:
        meta = json.load(f)
        
    # --- TRANSFORMACIÓN CLAVE PARA EL FRONTEND ---
    # Convertimos rutas relativas locales en URLs absolutas que el frontend pueda consumir.
    # Si la portada es local, creamos la URL a nuestro endpoint de portadas.
    if "coverUrl" in meta and not meta["coverUrl"].startswith("http"):
         # Asumimos que la ruta guardada es algo como "/cover/imagen.jpg"
         filename = meta["coverUrl"].split('/')[-1]
         meta["coverUrl"] = f"/api/books/{book_id}/cover/{filename}"

    # Añadimos siempre la URL de descarga del EPUB
    meta["epubUrl"] = f"/api/books/{book_id}/download"
    
    return meta


def load_all_books_meta() -> List[Dict[str, Any]]:
    books = []
    if BOOKS_DIR.exists():
        for book_folder in sorted(BOOKS_DIR.iterdir()):
            if not book_folder.is_dir():
                continue
            
            # Reutilizamos la función individual para asegurar que las URLs se generen bien
            meta = load_book_meta(book_folder.name)
            if meta:
                meta["source"] = "local"
                books.append(meta)
    return books

# ======================
# Endpoints
# ======================

@books_bp.get("")
def get_books():
    """Retorna la lista de libros con URLs listas para el frontend."""
    return jsonify(load_all_books_meta())


@books_bp.get("/<book_id>")
def get_book(book_id: str):
    meta = load_book_meta(book_id)
    if not meta:
        abort(404, description="Libro no encontrado")
    return jsonify(meta)


@books_bp.get("/<book_id>/download")
def download_book(book_id: str):
    """
    Endpoint crítico para el Reader:
    Sirve el archivo .epub binario para que epub.js lo procese.
    """
    book_folder = BOOKS_DIR / book_id
    try:
        # Buscamos cualquier archivo .epub en la carpeta
        files = list(book_folder.glob("*.epub"))
        if not files:
            abort(404, description="Archivo EPUB no encontrado en el servidor")
        
        # Enviamos el archivo
        return send_from_directory(book_folder, files[0].name)
    except Exception as e:
        abort(500, description=str(e))


@books_bp.get("/<book_id>/cover/<filename>")
def get_book_cover(book_id: str, filename: str):
    """Sirve la imagen de portada."""
    return send_from_directory(BOOKS_DIR / book_id, filename)


@books_bp.route('/upload', methods=['POST'])
def upload_book():
    # Mantenemos tu lógica futura de Firebase aquí
    return jsonify({'error': 'Endpoint en mantenimiento'}), 503
