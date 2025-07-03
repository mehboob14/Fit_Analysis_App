FROM python:3.11


RUN apt-get update && apt-get install -y \
  wget xvfb libgl1 libnss3 libatk1.0-0 libatk-bridge2.0-0 \
  libcups2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 \
  libgbm1 libgtk-3-0 libasound2 libpango-1.0-0 libcairo2 \
  libgdk-pixbuf2.0-0 libwoff1 libvpx7 libopus0 libgstreamer1.0-0 \
  libgraphene-1.0-0 libsecret-1-0 fonts-liberation libdrm2 \
  libxshmfence1 xdg-utils \
  libdbus-glib-1-2 libxt6 libx11-xcb1 libxcb-dri3-0 libxcb-shm0 \
  libgtk-4-1 \
  libgstreamer-plugins-base1.0-0 \
  libgstreamer-plugins-good1.0-0 \
  libgstreamer-plugins-bad1.0-0 \
  libgstreamer-plugins-ugly1.0-0 \
  gstreamer1.0-libav \
  gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad \
  gstreamer1.0-plugins-ugly \
  libflite1 \
  libenchant-2-2 \
  libhyphen0 \
  libmanette-0.2-0 \
  libgles2-mesa \
  libharfbuzz-icu0 \
  libavif15 \
  libx264-155 \
  --no-install-recommends \
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
