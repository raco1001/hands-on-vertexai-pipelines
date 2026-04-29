FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.5.1

COPY main.py .

ENTRYPOINT ["python", "main.py"]
