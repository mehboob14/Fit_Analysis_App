# ✅ 1) Use the official Playwright Python base image
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# ✅ 2) Set the working directory
WORKDIR /app

# ✅ 3) Install your Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ✅ 4) Copy your app code
COPY . .

# ✅ 5) Expose the port
EXPOSE 8000


CMD ["gunicorn", "app:app", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "1", \
     "--threads", "2", \
     "--timeout", "300", \
     "--graceful-timeout", "30", \
     "--log-level", "debug", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
