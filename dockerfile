FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    curl \
    wget \
    unzip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Установка Xray
RUN wget https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip \
    && unzip Xray-linux-64.zip -d /usr/local/bin/ \
    && rm Xray-linux-64.zip \
    && chmod +x /usr/local/bin/xray

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /var/log

CMD ["python", "src/main.py"]
