FROM python:3.11-slim-bookworm

# Предотвращение буферизации вывода Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Установка системных зависимостей для Playwright и сетевых утилит
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    gnupg \
    ca-certificates \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Копирование требований и установка Python-пакетов
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Установка Chromium для Playwright
RUN playwright install chromium

# Копирование исходного кода приложения
COPY . .

# Создание директории отчетов
RUN mkdir -p reports

CMD ["python", "main.py"]
