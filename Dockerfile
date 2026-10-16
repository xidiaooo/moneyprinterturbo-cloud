FROM python:3.12-slim

# ffmpeg is required by MoneyPrinterTurbo for video assembly
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Hugging Face Spaces expects the app on port 7860
ENV PORT=7860

CMD ["python", "entrypoint.py"]
