"""data-preparation 이 만든 train 텐서로 간단한 CNN 을 학습한다."""

import argparse
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset


class SimpleCNN(nn.Module):
    """CIFAR-10 용 아주 단순한 CNN (Conv-Pool-Conv-Pool-FC-FC)."""

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
    parser.add_argument("--train-input", required=True, help="train 텐서 경로")
    parser.add_argument("--model-output", required=True, help="학습된 모델 저장 경로")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1e-3)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[train] device = {device}")

    images, labels = torch.load(args.train_input, weights_only=True)
    loader = DataLoader(
        TensorDataset(images, labels), batch_size=args.batch_size, shuffle=True
    )

    model = SimpleCNN().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = nn.CrossEntropyLoss()

    for epoch in range(args.epochs):
        model.train()
        total_loss = 0.0
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            logits = model(x)
            loss = loss_fn(logits, y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * x.size(0)
        avg = total_loss / len(loader.dataset)
        print(f"[train] epoch {epoch + 1}/{args.epochs}  loss={avg:.4f}")

    Path(args.model_output).parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), args.model_output)
    print(f"[train] saved model -> {args.model_output}")


if __name__ == "__main__":
    main()
