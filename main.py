import os
from pathlib import Path

from flask import Flask, send_file, jsonify
from flask_cors import CORS

# Importa el Blueprint de libros
from services.books import books_bp

BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"

app = Flask(__name__)

# Permitir peticiones desde tu frontend (ajusta origins si quieres restringir)
CORS(app, resources={r"/api/*": {"origins": "*"}})


@app.route("/")
def index():
    """
    Ruta raíz de prueba.
    Si existe src/index.html (el hello world de la plantilla), lo sirve.
    Si no, devuelve un JSON simple indicando que el backend está corriendo.
    """
    index_path = SRC_DIR / "index.html"
    if index_path.exists():
        return send_file(index_path)
    return jsonify({"message": "Backend h-equity reads está corriendo"})


@app.get("/api/health")
def health():
    """Endpoint simple de health-check."""
    return jsonify({"status": "ok"})


# Registrar el blueprint de libros:
# /api/books
# /api/books/<book_id>
# /api/books/<book_id>/chapters/<n>
app.register_blueprint(books_bp)


def main():
    # host 0.0.0.0 por si lo corres en Docker/Cloud Run
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)


if __name__ == "__main__":
    main()
