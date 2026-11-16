# syntax=docker/dockerfile:1
#
# Agente AlquiHerramientas (TP Final) — imagen de la API.
#
#   docker compose up --build                  levanta la API en http://localhost:8000
#   docker build --target test .               corre la suite de tests dentro de la imagen
#
# La imagen lleva solo app/: ni tests, ni entregas archivadas, ni datos, ni claves. Las claves
# las pasa docker compose desde .env al arrancar; los datos viven en un volumen.

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ANONYMIZED_TELEMETRY=False

WORKDIR /srv/alquiherramientas

# Dependencias primero: si solo cambia el código, Docker reusa esta capa y no reinstala nada.
COPY requirements-app.txt .
RUN pip install -r requirements-app.txt

COPY app/ ./app/


# --- test: la suite completa (seguridad + arquitectura) dentro del mismo entorno que producción ---
FROM base AS test
RUN pip install httpx==0.28.1 pytest==9.2.0
COPY pytest.ini ./
COPY tests/ ./tests/
RUN python -m pytest -q -p no:cacheprovider


# --- produccion (target por defecto: es la última etapa) ---
FROM base AS produccion

# Usuario sin privilegios. data/ es donde el sistema escribe (índice vectorial, base SQL, memoria,
# logs); se crea acá con el dueño correcto para que el volumen la herede.
RUN useradd --create-home --uid 1000 agente \
    && mkdir -p data \
    && chown agente:agente data
USER agente

EXPOSE 8000

# start-period largo: el primer arranque construye el índice vectorial (embeddings) dentro del volumen.
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
