FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y    wget    gnupg    ca-certificates    fonts-liberation    libasound2    libatk-bridge2.0-0    libdrm2    libgtk-3-0    libnspr4    libnss3    libxss1    libxtst6    xdg-utils    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

RUN mkdir -p ./sessions ./downloads

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["python", "main.py"]
