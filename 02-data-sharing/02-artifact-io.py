"""KFP 의 Input / Output 아티팩트로 데이터를 공유하는 파이프라인.

- 컴포넌트는 `Output[Dataset]` / `Input[Dataset]` 타입으로 아티팩트를 주고받는다.
- 실제 저장 위치(파이프라인 루트 하위 GCS 경로)는 KFP 가 자동으로 할당한다.
- 장점: Vertex AI 가 자동으로 lineage / metadata 를 추적하고, UI 에 자료형별로
        아티팩트가 노출된다.
- 단점: 컴포넌트가 저장 경로를 직접 통제하지 못한다.
"""

from pathlib import Path

from kfp import compiler, dsl
from kfp.dsl import Dataset, Input, Output


# ---------------------------------------------------------------------------
# 1) 데이터 생성 컴포넌트
#    - `Output[Dataset]` 아티팩트에 CSV 를 써서 내보낸다.
#    - metadata 에 부가 정보를 기록해 두면 UI 와 후속 컴포넌트에서 활용 가능.
# ---------------------------------------------------------------------------
@dsl.component(
    base_image="python:3.12-slim",
    packages_to_install=["pandas==2.2.2"],
)
def produce_artifact(
    num_rows: int,
    output_dataset: Output[Dataset],
) -> None:
    import pandas as pd

    df = pd.DataFrame(
        {"id": range(num_rows), "value": [i * 10 for i in range(num_rows)]}
    )
    df.to_csv(output_dataset.path, index=False)

    output_dataset.metadata["num_rows"] = num_rows
    output_dataset.metadata["format"] = "csv"
    print(f"[produce] wrote {num_rows} rows to {output_dataset.path}")


# ---------------------------------------------------------------------------
# 2) 데이터 활용 컴포넌트
#    - `Input[Dataset]` 으로 선행 컴포넌트의 아티팩트를 주입받는다.
#    - `.path` 로 로컬에 마운트된 파일 경로처럼 읽으면 된다.
# ---------------------------------------------------------------------------
@dsl.component(
    base_image="python:3.12-slim",
    packages_to_install=["pandas==2.2.2"],
)
def consume_artifact(input_dataset: Input[Dataset]) -> float:
    import pandas as pd

    df = pd.read_csv(input_dataset.path)
    mean_value = float(df["value"].mean())

    print(f"[consume] read {len(df)} rows from {input_dataset.uri}")
    print(f"[consume] metadata: {input_dataset.metadata}")
    print(f"[consume] mean(value) = {mean_value}")
    return mean_value


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
@dsl.pipeline(
    name="data-sharing-artifact-io",
    description="Input/Output 아티팩트로 데이터를 공유하는 예제",
)
def artifact_io_pipeline(num_rows: int = 50):
    produce_task = produce_artifact(num_rows=num_rows)
    consume_artifact(
        input_dataset=produce_task.outputs["output_dataset"],
    )


if __name__ == "__main__":
    output_path = Path(__file__).parent / "artifact-io.yaml"
    compiler.Compiler().compile(
        pipeline_func=artifact_io_pipeline,
        package_path=str(output_path),
    )
