FROM python:3.14-slim

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY main.py .

CMD ["python", "main.py"]
