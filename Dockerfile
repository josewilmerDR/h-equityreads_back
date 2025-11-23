# Usamos una imagen oficial de Python ligera
FROM python:3.10-slim

# 1. INSTALAMOS PANDOC
# Esto es lo que te faltaba. Cloud Run ejecuta esto al construir tu imagen.
# 'apt-get update' refresca la lista de paquetes y luego instalamos pandoc.
RUN apt-get update && apt-get install -y \
    pandoc \
    && rm -rf /var/lib/apt/lists/*

# 2. Configurar el directorio de trabajo en el contenedor
WORKDIR /app

# 3. Copiar y instalar dependencias de Python
# Copiamos primero solo el requirements.txt para aprovechar la caché de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copiar el resto de tu código al contenedor
COPY . .

# 5. Comando para arrancar tu aplicación Flask
# Cloud Run inyecta la variable de entorno PORT (por defecto 8080)
# Usamos 'gunicorn' que es servidor de producción (asegúrate de añadir gunicorn a requirements.txt)
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app