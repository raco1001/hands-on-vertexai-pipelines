# PyTorch 공식 CUDA 런타임 이미지. GPU 가 붙으면 CUDA 가속, GPU 가 없으면 자동으로
# CPU 로 fallback (main.py 의 `torch.device('cuda' if torch.cuda.is_available() else 'cpu')`).
# 이 이미지에는 torch / torchvision 이 이미 포함되어 있어 별도 pip install 불필요.
FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime

WORKDIR /app

COPY main.py .

ENTRYPOINT ["python", "main.py"]
