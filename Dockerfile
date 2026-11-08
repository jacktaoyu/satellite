FROM node:22-bookworm-slim AS frontend-build

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5001 \
    FRONTEND_DIST=/app/frontend/dist

WORKDIR /app
RUN pip install --no-cache-dir \
    Flask==3.0.0 \
    flask-cors==5.0.1 \
    Flask-SQLAlchemy==3.1.1 \
    SQLAlchemy==2.0.23 \
    waitress==3.0.2 \
    PyMySQL==1.1.1 \
    numpy==1.26.4 \
    pandas==2.1.3 \
    scipy==1.13.1 \
    openpyxl==3.1.5 \
    skyfield==1.53 \
    sgp4==2.24 \
    jplephem==2.22 \
    pyproj==3.6.1

COPY backend/ ./backend/
COPY --from=frontend-build /build/frontend/dist/ ./frontend/dist/

WORKDIR /app/backend
EXPOSE 5001 9999
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5001/health', timeout=5)" || exit 1
CMD ["python", "app.py"]
