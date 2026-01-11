FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# System dependencies for PDF processing and healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Çalışma dizini
WORKDIR /app

# Bağımlılıkları kopyala ve yükle (Cache avantajı için önce bunlar)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Uygulama kodlarını kopyala
COPY . .

# Portu aç
EXPOSE 8000

# Uygulamayı başlat
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]