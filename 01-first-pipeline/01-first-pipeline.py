"""KFP SDK v2 로 작성한 Vertex AI Pipeline.

하나의 파이프라인에서 세 가지 컴포넌트 작성 방식을 보여준다:
  1. Python 함수 기반 컴포넌트 (`@dsl.component`)
  2. Prebuilt 컨테이너 이미지 컴포넌트 (`dsl.ContainerSpec`)
  3. 입출력 의존성 대신 `.after(...)` 로 실행 순서를 강제하는 컴포넌트
"""

from kfp import compiler, dsl
from kfp.dsl import Dataset, Input, Output


# ---------------------------------------------------------------------------
# 1) Python 함수형 컴포넌트
#    - 함수 인자/리턴값이 그대로 컴포넌트 인터페이스가 된다.
#    - `packages_to_install` 로 런타임에 pip 패키지를 설치할 수 있다.
# ---------------------------------------------------------------------------
@dsl.component(
    base_image="python:3.12-slim",
    packages_to_install=["pandas==2.2.2"],
)
def generate_data(
    num_rows: int,
    output_dataset: Output[Dataset],
) -> str:
    """임의의 CSV 데이터를 만들어 Dataset 아티팩트로 저장한다."""
    import pandas as pd

    df = pd.DataFrame(
        {"id": range(num_rows), "value": [i * 2 for i in range(num_rows)]}
    )
    df.to_csv(output_dataset.path, index=False)
    output_dataset.metadata["num_rows"] = num_rows
    return output_dataset.path


# ---------------------------------------------------------------------------
# 2) Prebuilt 이미지를 실행하는 컨테이너 컴포넌트
#    - 이미 빌드되어 레지스트리에 올라가 있는 이미지를 실행한다.
#    - command / args 를 직접 지정하며, 입력 아티팩트 경로를 인자로 받는다.
# ---------------------------------------------------------------------------
@dsl.container_component
def process_data(
    input_dataset: Input[Dataset],
    processed_dataset: Output[Dataset],
    multiplier: int,
):
    return dsl.ContainerSpec(
        # Docker Hub 의 공식 busybox 이미지를 직접 참조한다.
        # 기존에 쓰이던 `gcr.io/google-containers/busybox:latest` 는 Schema 1 manifest 라
        # containerd v2.0 이 적용된 Vertex AI 워커에서 pull 이 거부되었고,
        # `mirror.gcr.io/...` 는 Vertex AI 의 이미지 URI 허용 regex 에 맞지 않아
        # submission 단계에서 반려된다.
        image="busybox:stable",
        command=["sh", "-c"],
        args=[
            (
                "echo 'processing '$0' with multiplier='$1;"
                "mkdir -p $(dirname $2);"
                "awk -F',' -v m=$1 'NR==1{print $0} NR>1{print $1\",\"$2*m}' $0 > $2"
            ),
            input_dataset.path,
            multiplier,
            processed_dataset.path,
        ],
    )


# ---------------------------------------------------------------------------
# 3) after() 로 강제 선후관계를 거는 컴포넌트
#    - 선행 컴포넌트의 출력을 인자로 받지 않기 때문에 KFP 가 자동으로
#      의존성을 추론할 수 없다. 따라서 `.after(task)` 로 순서를 강제한다.
# ---------------------------------------------------------------------------
@dsl.component(base_image="python:3.12-slim")
def notify(message: str) -> str:
    print(f"[notify] pipeline finished: {message}")
    return message


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
@dsl.pipeline(
    name="three-component-demo",
    description="function / container / after 세 가지 패턴을 보여주는 예제",
)
def three_component_pipeline(
    num_rows: int = 100,
    multiplier: int = 3,
    message: str = "done",
):
    # (1) 함수형 컴포넌트 실행
    gen_task = generate_data(num_rows=num_rows)

    # (2) 컨테이너 컴포넌트 실행
    #     gen_task.outputs["output_dataset"] 를 입력으로 넘기므로
    #     KFP 가 자동으로 gen_task -> proc_task 순서를 추론한다.
    proc_task = process_data(
        input_dataset=gen_task.outputs["output_dataset"],
        multiplier=multiplier,
    )

    # (3) after() 로 강제 선후관계 지정
    #     notify 는 proc_task 의 출력을 인자로 받지 않지만,
    #     .after(proc_task) 에 의해 proc_task 완료 후에 실행된다.
    notify(message=message).after(proc_task)


if __name__ == "__main__":
    # 현재 파일과 같은 폴더(01-first-pipeline/)에 YAML 을 생성한다.
    from pathlib import Path

    output_path = Path(__file__).parent / "first-pipeline.yaml"
    compiler.Compiler().compile(
        pipeline_func=three_component_pipeline,
        package_path=str(output_path),
    )
