import os
import json
from pathlib import Path

from flask import Flask, send_file, jsonify, abort
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
BOOKS_DIR = BASE_DIR / "src" / "data" / "books"

app = Flask(__name__)

# Permitir peticiones desde tu frontend
CORS(app)

@app.route("/")
def index():
    # Ajusta la ruta según dónde tengas tu build de React
    return send_file(BASE_DIR / "src" / "index.html")


# --------- UTILIDADES ---------
def load_book_file(book_id: str):
    path = BOOKS_DIR / f"{book_id}.json"
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def list_books():
    books = []
    for path in BOOKS_DIR.glob("*.json"):
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        books.append({
            "id": data["id"],
            "title": data["title"],
            "author": data.get("author", ""),
            "coverUrl": data.get("coverUrl", ""),
            "description": data.get("description", "")
        })
    return books


# --------- API ---------
@app.get("/api/books")
def api_list_books():
    return jsonify(list_books())


@app.get("/api/books/<book_id>")
def api_get_book(book_id):
    data = load_book_file(book_id)
    if data is None:
        abort(404)

    # Solo metadatos + lista de capítulos
    response = {
        "id": data["id"],
        "title": data["title"],
        "author": data.get("author", ""),
        "description": data.get("description", ""),
        "coverUrl": data.get("coverUrl", ""),
        "chapters": [
            {"number": c["number"], "title": c.get("title", f"Capítulo {c['number']}")}
            for c in data.get("chapters", [])
        ],
    }
    return jsonify(response)


@app.get("/api/books/<book_id>/chapters/<int:number>")
def api_get_chapter(book_id, number):
    data = load_book_file(book_id)
    if data is None:
        abort(404)
    chapter = next(
        (c for c in data.get("chapters", []) if c["number"] == number),
        None
    )
    if chapter is None:
        abort(404)

    # Devuelve contenido completo
    return jsonify({
        "bookId": data["id"],
        "number": chapter["number"],
        "title": chapter.get("title", f"Capítulo {chapter['number']}"),
        "contentHtml": chapter.get("contentHtml", "")
    })


def main():
    app.run(port=int(os.environ.get("PORT", 5000)), debug=True)


if __name__ == "__main__":
    main()
