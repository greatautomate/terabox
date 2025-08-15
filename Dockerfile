# Use Ubuntu instead of Debian for better Playwright compatibility
FROM ubuntu:22.04

WORKDIR /app

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies manually (Ubuntu packages)
RUN apt-get update && apt-get install -y \
    # Basic tools
    wget \
    curl \
    gnupg \
    ca-certificates \
    python3 \
    python3-pip \
    python3-venv \
    # Playwright browser dependencies
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    # Additional dependencies for headless mode
    libgconf-2-4 \
    libgdk-pixbuf2.0-0 \
    libglib2.0-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libappindicator1 \
    # Fonts
    fonts-liberation \
    fonts-dejavu-core \
    fontconfig \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Create symlink for python command
RUN ln -s /usr/bin/python3 /usr/bin/python

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Install Playwright browsers (without install-deps)
RUN playwright install chromium

COPY . .

RUN mkdir -p ./sessions ./downloads

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set display for headless mode
ENV DISPLAY=:99

CMD ["python", "main.py"]
