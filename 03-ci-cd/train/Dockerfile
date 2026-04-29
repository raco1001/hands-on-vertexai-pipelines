FROM python:3.12-slim

WORKDIR /app

# CPU 전용 PyTorch 휠. GPU 를 사용할 예정이면 base image 를
# `pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime` 등으로 교체하고
# 아래 pip install 라인을 제거하면 된다.
RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.5.1

COPY main.py .

ENTRYPOINT ["python", "main.py"]
