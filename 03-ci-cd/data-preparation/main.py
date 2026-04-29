"""CIFAR-10 데이터를 내려받아 train / test 텐서를 아티팩트 경로로 저장한다."""

import argparse
from pathlib import Path

import torch
from torchvision import datasets, transforms


def dataset_to_tensors(ds) -> tuple[torch.Tensor, torch.Tensor]:
    images = torch.stack([img for img, _ in ds])
    labels = torch.tensor([lbl for _, lbl in ds], dtype=torch.long)
    return images, labels


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-output", required=True, help="train 텐서 저장 경로")
    parser.add_argument("--test-output", required=True, help="test 텐서 저장 경로")
    parser.add_argument("--data-dir", default="/tmp/cifar10")
    args = parser.parse_args()

    transform = transforms.Compose(
        [
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
        ]
    )

    train_ds = datasets.CIFAR10(
        root=args.data_dir, train=True, download=True, transform=transform
    )
    test_ds = datasets.CIFAR10(
        root=args.data_dir, train=False, download=True, transform=transform
    )

    Path(args.train_output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.test_output).parent.mkdir(parents=True, exist_ok=True)

    torch.save(dataset_to_tensors(train_ds), args.train_output)
    torch.save(dataset_to_tensors(test_ds), args.test_output)

    print(f"[data-prep] train({len(train_ds)}) -> {args.train_output}")
    print(f"[data-prep] test ({len(test_ds)}) -> {args.test_output}")


if __name__ == "__main__":
    main()
