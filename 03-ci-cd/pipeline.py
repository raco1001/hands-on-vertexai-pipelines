"""CI/CD 로 관리되는 CIFAR-10 파이프라인.

구성:
  1. data-preparation : CIFAR-10 다운로드 → train/test 텐서 아티팩트 생성
  2. train            : 간단한 CNN 학습 → 모델 아티팩트 생성
  3. evaluation       : 학습된 모델로 test accuracy 계산 → metrics 아티팩트 생성

세 컴포넌트 모두 별도 Docker 이미지로 빌드된다. 이미지 태그는 컴파일 시점에
환경변수로 주입되어, CI/CD 에서 빌드한 특정 커밋 기준 이미지를 그대로 참조한다.

각 컴포넌트가 **독립적인 태그** 를 갖는 이유는 monorepo CI 에서 변경되지 않은
컴포넌트는 재빌드하지 않고 기존 이미지를 그대로 재사용하기 위함이다. CI 워크플로우는
각 폴더를 마지막으로 건드린 커밋의 short SHA 를 해당 컴포넌트의 태그로 사용한다.

  - IMAGE_REGISTRY  : 예) us-central1-docker.pkg.dev/<project>/vertex-ci-images
  - DATA_PREP_TAG   : data-preparation 이미지 태그
  - TRAIN_TAG       : train 이미지 태그
  - EVAL_TAG        : evaluation 이미지 태그
"""

import os
from pathlib import Path

from kfp import compiler, dsl
from kfp.dsl import Dataset, Input, Metrics, Model, Output


# 기본값은 의미 있는 placeholder 일 뿐, CI 에서는 항상 환경변수로 덮어쓴다.
IMAGE_REGISTRY = os.environ.get(
    "IMAGE_REGISTRY",
    "us-central1-docker.pkg.dev/REPLACE-WITH-PROJECT/vertex-ci-images",
)

# 컴포넌트별 태그 — 각 컴포넌트 폴더의 last-touch 커밋 short SHA 가 들어온다.
DATA_PREP_TAG = os.environ.get("DATA_PREP_TAG", "latest")
TRAIN_TAG = os.environ.get("TRAIN_TAG", "latest")
EVAL_TAG = os.environ.get("EVAL_TAG", "latest")


# ---------------------------------------------------------------------------
# 컨테이너 컴포넌트 정의 — 각자 별도 이미지를 실행한다.
# 데이터는 Input/Output 아티팩트 경로를 CLI 인자로 넘겨서 공유한다.
# ---------------------------------------------------------------------------
@dsl.container_component
def data_preparation(
    train_dataset: Output[Dataset],
    test_dataset: Output[Dataset],
):
    return dsl.ContainerSpec(
        image=f"{IMAGE_REGISTRY}/data-preparation:{DATA_PREP_TAG}",
        command=["python", "main.py"],
        args=[
            "--train-output",
            train_dataset.path,
            "--test-output",
            test_dataset.path,
        ],
    )


@dsl.container_component
def train(
    train_dataset: Input[Dataset],
    model: Output[Model],
    epochs: int,
    batch_size: int,
    lr: float,
):
    return dsl.ContainerSpec(
        image=f"{IMAGE_REGISTRY}/train:{TRAIN_TAG}",
        command=["python", "main.py"],
        args=[
            "--train-input",
            train_dataset.path,
            "--model-output",
            model.path,
            "--epochs",
            epochs,
            "--batch-size",
            batch_size,
            "--lr",
            lr,
        ],
    )


@dsl.container_component
def evaluation(
    test_dataset: Input[Dataset],
    model: Input[Model],
    metrics: Output[Metrics],
):
    return dsl.ContainerSpec(
        image=f"{IMAGE_REGISTRY}/evaluation:{EVAL_TAG}",
        command=["python", "main.py"],
        args=[
            "--test-input",
            test_dataset.path,
            "--model-input",
            model.path,
            "--metrics-output",
            metrics.path,
        ],
    )


# ---------------------------------------------------------------------------
# Pipeline
#   - 하이퍼파라미터 + 각 컴포넌트의 컴퓨팅 스펙을 파이프라인 파라미터로 노출한다.
#   - 제출 시 `--param cpu_train=8 --param memory_train=32G ...` 로 오버라이드.
# ---------------------------------------------------------------------------
@dsl.pipeline(
    name="ci-cd-cifar10",
    description="data-prep / train / eval 3단계 CIFAR-10 CNN 파이프라인",
)
def ci_cd_pipeline(
    # --- 학습 하이퍼파라미터 ---
    epochs: int = 3,
    batch_size: int = 128,
    lr: float = 1e-3,
    # --- data-preparation 컴퓨팅 스펙 ---
    cpu_prep: str = "2",
    memory_prep: str = "8G",
    # --- train 컴퓨팅 스펙 ---
    cpu_train: str = "4",
    memory_train: str = "16G",
    # --- evaluation 컴퓨팅 스펙 ---
    cpu_eval: str = "2",
    memory_eval: str = "8G",
):
    # 1) data-preparation
    prep_task = data_preparation()
    prep_task.set_cpu_limit(cpu_prep).set_memory_limit(memory_prep)

    # 2) train — prep 의 train_dataset 아티팩트를 입력으로 받는다.
    train_task = train(
        train_dataset=prep_task.outputs["train_dataset"],
        epochs=epochs,
        batch_size=batch_size,
        lr=lr,
    )
    train_task.set_cpu_limit(cpu_train).set_memory_limit(memory_train)
    # GPU 를 붙이려면 아래 두 줄의 주석을 풀고 이미지도 CUDA base 로 교체한다:
    # train_task.set_accelerator_type("NVIDIA_TESLA_T4")
    # train_task.set_accelerator_limit(1)

    # 3) evaluation — prep 의 test_dataset + train 의 model 을 입력으로 받는다.
    eval_task = evaluation(
        test_dataset=prep_task.outputs["test_dataset"],
        model=train_task.outputs["model"],
    )
    eval_task.set_cpu_limit(cpu_eval).set_memory_limit(memory_eval)


if __name__ == "__main__":
    output_path = Path(__file__).parent / "ci-cd-pipeline.yaml"
    compiler.Compiler().compile(
        pipeline_func=ci_cd_pipeline,
        package_path=str(output_path),
    )
    print(f"compiled -> {output_path}")
    print(f"  IMAGE_REGISTRY = {IMAGE_REGISTRY}")
    print(f"  DATA_PREP_TAG  = {DATA_PREP_TAG}")
    print(f"  TRAIN_TAG      = {TRAIN_TAG}")
    print(f"  EVAL_TAG       = {EVAL_TAG}")
