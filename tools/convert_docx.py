import pypandoc
from pathlib import Path
import os

# Configuración
BASE_DIR = Path(__file__).resolve().parent.parent
SOURCE_DOCS = BASE_DIR / "data" / "source_docs"

def convert_all_docx():
    """
    Busca todos los archivos .docx en data/source_docs
    y los convierte a .epub usando Pandoc.
    """
    print(f"🔍 Buscando archivos .docx en: {SOURCE_DOCS}")
    
    # Asegurarnos de que existe el directorio
    if not SOURCE_DOCS.exists():
        print(f"❌ El directorio {SOURCE_DOCS} no existe.")
        return

    docx_files = list(SOURCE_DOCS.glob("*.docx"))
    
    if not docx_files:
        print("⚠️  No se encontraron archivos .docx para procesar.")
        return

    count = 0
    for docx_path in docx_files:
        # Definir nombre de salida (mismo nombre pero .epub)
        epub_name = docx_path.stem + ".epub"
        epub_output_path = SOURCE_DOCS / epub_name
        
        # Verificar si ya existe para no repetir trabajo innecesario
        if epub_output_path.exists():
            print(f"⏭️  Saltando {docx_path.name} (ya existe el .epub)")
            continue
            
        print(f"🔄 Convirtiendo: {docx_path.name}...")
        
        try:
            # Convertimos usando pypandoc
            # --toc genera una tabla de contenidos automática
            # --metadata title=... usa el nombre del archivo como título si no tiene
            pypandoc.convert_file(
                str(docx_path), 
                'epub', 
                outputfile=str(epub_output_path),
                extra_args=['--toc', f'--metadata=title:{docx_path.stem}'] 
            )
            print(f"✅ Éxito: Generado {epub_name}")
            count += 1
        except Exception as e:
            print(f"❌ Error al convertir {docx_path.name}: {e}")
            print("   (Asegúrate de que pandoc esté instalado en el sistema)")

    if count > 0:
        print(f"\n✨ Se convirtieron {count} libros a EPUB exitosamente.")
        print("👉 Ahora ejecuta: python tools/ingest_epub.py para importarlos al sistema.")
    else:
        print("\n✅ Todos los documentos .docx ya tienen su versión .epub.")

if __name__ == "__main__":
    convert_all_docx()
