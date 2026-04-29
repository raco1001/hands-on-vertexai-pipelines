"""학습된 모델을 test 텐서로 평가하고 metrics 아티팩트(JSON)를 저장한다."""

import argparse
import json
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset


class SimpleCNN(nn.Module):
    """train/main.py 와 동일한 아키텍처 (state_dict 호환을 위해 그대로 복사)."""

    def __init__(self, num_classes: int = 10) -> None:
        super().__init__()
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.fc1 = nn.Linear(64 * 8 * 8, 128)
        self.fc2 = nn.Linear(128, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = x.flatten(1)
        x = F.relu(self.fc1(x))
        return self.fc2(x)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-input", required=True, help="test 텐서 경로")
    parser.add_argument("--model-input", required=True, help="학습된 모델 경로")
    parser.add_argument("--metrics-output", required=True, help="metrics JSON 저장 경로")
    parser.add_argument("--batch-size", type=int, default=256)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    images, labels = torch.load(args.test_input, weights_only=True)
    loader = DataLoader(TensorDataset(images, labels), batch_size=args.batch_size)

    model = SimpleCNN().to(device)
    state = torch.load(args.model_input, map_location=device, weights_only=True)
    model.load_state_dict(state)
    model.eval()

    correct = 0
    total = 0
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            preds = model(x).argmax(dim=1)
            correct += (preds == y).sum().item()
            total += y.size(0)

    accuracy = correct / total
    print(f"[eval] accuracy = {accuracy:.4f}  ({correct}/{total})")

    Path(args.metrics_output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.metrics_output, "w") as f:
        json.dump(
            {"accuracy": accuracy, "correct": correct, "total": total},
            f,
            indent=2,
        )


if __name__ == "__main__":
    main()
