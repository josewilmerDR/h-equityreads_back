# services/books.py
import os
import json
import tempfile
import pypandoc
from pathlib import Path
from typing import List, Optional, Dict, Any

# --- NUEVOS IMPORTS PARA SUBIDA Y FIREBASE ---
from flask import Blueprint, jsonify, abort, request
from werkzeug.utils import secure_filename
from firebase_admin import storage, firestore

# Creamos un Blueprint para agrupar todas las rutas de libros
books_bp = Blueprint("books", __name__, url_prefix="/api/books")

# ======================
# Directorios del backend (Legacy Local)
# ======================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BOOKS_DIR = DATA_DIR / "books"


# ======================
# Helpers (Legacy Local)
# ======================

def load_book_meta(book_id: str) -> Optional[Dict[str, Any]]:
    """Carga el meta.json de un libro local."""
    meta_path = BOOKS_DIR / book_id / "meta.json"
    if not meta_path.exists():
        return None

    with meta_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_all_books_meta() -> List[Dict[str, Any]]:
    """Devuelve la lista de libros locales y DEBERÍA fusionar con Firestore (Pendiente v2)."""
    books = []

    # 1. Cargar libros locales (Tu código actual)
    if BOOKS_DIR.exists():
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
                "source": "local" # Marcador para saber de dónde viene
            })
    
    # NOTA: Aquí podrías añadir una consulta a Firestore para concatenar 
    # los libros subidos a la nube en esta misma lista.
    
    return books


def load_chapter(book_id: str, number: int) -> Optional[Dict[str, Any]]:
    """Carga el contenido HTML de un capítulo (Legacy)."""
    meta = load_book_meta(book_id)
    if not meta:
        return None

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
# Endpoints de Lectura
# ======================

@books_bp.get("")
def get_books():
    """GET /api/books → lista de libros."""
    return jsonify(load_all_books_meta())


@books_bp.get("/<book_id>")
def get_book(book_id: str):
    """GET /api/books/<book_id> → detalle del libro."""
    meta = load_book_meta(book_id)
    # Si no está en local, aquí deberías buscar en Firestore (Pendiente)
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


# ======================
# NUEVO ENDPOINT: Subida y Conversión
# ======================

@books_bp.route('/upload', methods=['POST'])
def upload_book():
    """
    Recibe un archivo (.docx o .epub), lo convierte a EPUB si es necesario,
    lo sube a Firebase Storage y guarda la referencia en Firestore.
    """
    # Inicializamos los clientes aquí dentro para evitar problemas de importación circular
    # ya que main.py inicializa la app después de importar este archivo.
    try:
        db = firestore.client()
        bucket = storage.bucket()
    except Exception as e:
        return jsonify({'error': 'Error conectando con Firebase. Verifica credenciales.'}), 500

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    filename = secure_filename(file.filename)
    
    # Usamos un directorio temporal para procesar la conversión
    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, filename)
        file.save(input_path)
        
        final_filename = filename
        file_to_upload_path = input_path
        format_type = 'unknown'

        try:
            # CASO 1: Es un DOCX -> Convertir a EPUB con Pandoc
            if filename.endswith('.docx'):
                epub_filename = filename.replace('.docx', '.epub')
                output_path = os.path.join(temp_dir, epub_filename)
                
                print(f"Convirtiendo {filename} a EPUB...")
                # pypandoc requiere que 'pandoc' esté instalado en el sistema (Dockerfile)
                pypandoc.convert_file(input_path, 'epub', outputfile=output_path)
                
                final_filename = epub_filename
                file_to_upload_path = output_path
                format_type = 'converted_from_docx'

            # CASO 2: Ya es un EPUB -> Subir directo
            elif filename.endswith('.epub'):
                format_type = 'native_epub'
            
            else:
                return jsonify({'error': 'Formato no soportado. Use .docx o .epub'}), 400

            # 2. SUBIDA A FIREBASE STORAGE
            # Guardamos en la carpeta 'books/' dentro del bucket
            blob = bucket.blob(f"books/{final_filename}")
            blob.upload_from_filename(file_to_upload_path)
            blob.make_public() # Hace el archivo accesible por URL pública
            
            epub_url = blob.public_url

            # 3. GUARDADO EN FIRESTORE (Metadatos)
            # Creamos un documento en la colección 'books'
            new_book_ref = db.collection('books').add({
                'title': filename.rsplit('.', 1)[0].replace('-', ' ').title(),
                'author': 'Desconocido', # Podrías enviarlo en el form-data request.form['author']
                'url': epub_url,         # ESTA es la URL que usará react-reader
                'original_filename': filename,
                'format': 'epub',
                'source': 'cloud',       # Diferenciador para tu frontend
                'uploaded_at': firestore.SERVER_TIMESTAMP
            })

            return jsonify({
                'message': 'Libro procesado exitosamente', 
                'url': epub_url,
                'id': new_book_ref[1].id
            }), 200

        except OSError as e:
            if "pandoc" in str(e).lower():
                return jsonify({'error': 'Pandoc no encontrado. Asegurate de instalarlo en el Dockerfile.'}), 500
            return jsonify({'error': str(e)}), 500
        except Exception as e:
            print(f"Error procesando libro: {e}")
            return jsonify({'error': str(e)}), 500


# # services/books.py
# import json
# from pathlib import Path
# from typing import List, Optional, Dict, Any

# from flask import Blueprint, jsonify, abort

# # Creamos un Blueprint para agrupar todas las rutas de libros
# books_bp = Blueprint("books", __name__, url_prefix="/api/books")

# # ======================
# # Directorios del backend
# # ======================

# # /backend/services/books.py → parent = /backend/services
# # parent.parent = /backend
# BASE_DIR = Path(__file__).resolve().parent.parent

# DATA_DIR = BASE_DIR / "data"
# BOOKS_DIR = DATA_DIR / "books"


# # ======================
# # Helpers
# # ======================

# def load_book_meta(book_id: str) -> Optional[Dict[str, Any]]:
#     """Carga el meta.json de un libro."""
#     meta_path = BOOKS_DIR / book_id / "meta.json"
#     if not meta_path.exists():
#         return None

#     with meta_path.open("r", encoding="utf-8") as f:
#         return json.load(f)


# def load_all_books_meta() -> List[Dict[str, Any]]:
#     """Devuelve la lista de todos los libros (solo metadatos para catálogo)."""
#     books = []

#     if not BOOKS_DIR.exists():
#         return books

#     for book_folder in sorted(BOOKS_DIR.iterdir()):
#         if not book_folder.is_dir():
#             continue

#         meta_path = book_folder / "meta.json"
#         if not meta_path.exists():
#             continue

#         with meta_path.open("r", encoding="utf-8") as f:
#             meta = json.load(f)

#         books.append({
#             "id": meta.get("id"),
#             "title": meta.get("title"),
#             "author": meta.get("author"),
#             "description": meta.get("description", ""),
#             "coverUrl": meta.get("coverUrl", ""),
#             "chaptersCount": meta.get("chaptersCount", 0),
#         })

#     return books


# def load_chapter(book_id: str, number: int) -> Optional[Dict[str, Any]]:
#     """Carga el contenido HTML de un capítulo."""
#     meta = load_book_meta(book_id)
#     if not meta:
#         return None

#     # Buscar título de capítulo si está en el meta.json
#     chapter_title = None
#     for ch in meta.get("chapters", []):
#         if ch.get("number") == number:
#             chapter_title = ch.get("title")
#             break

#     chapter_path = BOOKS_DIR / book_id / "chapters" / f"{number}.html"
#     if not chapter_path.exists():
#         return None

#     with chapter_path.open("r", encoding="utf-8") as f:
#         content_html = f.read()

#     return {
#         "bookId": book_id,
#         "number": number,
#         "title": chapter_title or f"Capítulo {number}",
#         "contentHtml": content_html,
#     }


# # ======================
# # Endpoints del Blueprint
# # ======================

# @books_bp.get("")
# def get_books():
#     """GET /api/books → lista de libros."""
#     return jsonify(load_all_books_meta())


# @books_bp.get("/<book_id>")
# def get_book(book_id: str):
#     """GET /api/books/<book_id> → detalle del libro."""
#     meta = load_book_meta(book_id)
#     if not meta:
#         abort(404, description="Libro no encontrado")

#     return jsonify(meta)


# @books_bp.get("/<book_id>/chapters/<int:number>")
# def get_book_chapter(book_id: str, number: int):
#     """GET /api/books/<id>/chapters/<n> → contenido de capítulo."""
#     chapter = load_chapter(book_id, number)
#     if not chapter:
#         abort(404, description="Capítulo no encontrado")

#     return jsonify(chapter)
