FROM python:3.11-slim

# ffmpeg video kaatne ke liye, fonts caption (Hindi/English) ke liye
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg fontconfig fonts-noto-core \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=10000 \
    CAPTION_FONT="Noto Sans" \
    WHISPER_MODEL=base

# ek worker, kaafi threads: jobs memory me rakhe jaate hain isliye ek hi process chahiye
CMD gunicorn app:app --bind 0.0.0.0:${PORT} --workers 1 --threads 8 --timeout 900
