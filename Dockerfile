FROM python:3.11


RUN apt-get update && apt-get install -y \
    wget xvfb libgl1 libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libgtk-3-0 libasound2 libpango-1.0-0 libcairo2 \
    libgdk-pixbuf2.0-0 libwoff1 libvpx7 libopus0 libgstreamer1.0-0 \
    libgraphene-1.0-0 libsecret-1-0 fonts-liberation libdrm2 \
    libxshmfence1 xdg-utils --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*


WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


RUN playwright install

COPY . .

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", \
     "Xvfb :99 & \
      export DISPLAY=:99 && \
      gunicorn app:app \
        --bind 0.0.0.0:8000 \
        --workers 1 \
        --threads 2 \
        --timeout 300 \
        --graceful-timeout 30 \
        --log-level debug \
        --access-logfile '-' \
        --error-logfile '-'"]
