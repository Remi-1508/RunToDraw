# Image du backend RunToDraw (API FastAPI). Construite depuis le dossier backend/ :
#   docker build -t runtodraw-api backend
#   docker run --rm -p 8000:8000 -e RUNTODRAW_TRUSTED_PROXY_HOPS=0 runtodraw-api
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Les dépendances d'abord : cette couche est réutilisée tant que requirements.txt ne change pas.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Seul le paquet de l'API est copié (ni les tests, ni les outils, ni matplotlib).
COPY runtodraw ./runtodraw

# L'application ne tourne pas en administrateur.
RUN useradd --create-home --uid 1000 appuser
USER appuser

# L'hébergeur (Render) fournit le port dans PORT ; 8000 par défaut en local.
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/health')" || exit 1
CMD ["sh", "-c", "uvicorn runtodraw.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
