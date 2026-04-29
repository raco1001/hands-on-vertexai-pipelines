"""GCS Fuse 마운트로 데이터를 공유하는 파이프라인.

- Vertex AI Pipelines 는 기본적으로 모든 GCS 버킷을 컨테이너 내부의
  `/gcs/<bucket>/...` 경로에 Cloud Storage FUSE 로 마운트해준다.
  (공식 문서: https://cloud.google.com/vertex-ai/docs/pipelines/gcs-fuse)
- 컴포넌트는 일반 로컬 파일처럼 read/write 만 하면 되며, SDK 호출이 필요 없다.
- 장점: 대용량 파일을 스트리밍으로 처리하기 쉽고, GCS 클라이언트 코드가 사라진다.
- 단점: 랜덤 쓰기 / rename 등 POSIX 전체를 지원하지는 않음. 읽기 중심에 적합.
"""

from pathlib import Path

from kfp import compiler, dsl


# ---------------------------------------------------------------------------
# 1) 데이터 생성 컴포넌트
#    - `/gcs/<bucket>/<file_name>` 경로에 그냥 파일을 쓴다.
#    - 해당 경로는 자동으로 `gs://<bucket>/<file_name>` 에 기록된다.
# ---------------------------------------------------------------------------
@dsl.component(base_image="python:3.12-slim")
def produce_to_fuse(bucket: str, file_name: str) -> str:
    import os

    fuse_path = f"/gcs/{bucket}/{file_name}"
    os.makedirs(os.path.dirname(fuse_path), exist_ok=True)

    with open(fuse_path, "w") as f:
        f.write("id,value\n")
        for i in range(5):
            f.write(f"{i},{i * 100}\n")

    print(f"[produce] wrote file via FUSE: {fuse_path}")
    return fuse_path


# ---------------------------------------------------------------------------
# 2) 데이터 활용 컴포넌트
#    - 선행 컴포넌트가 리턴한 FUSE 경로를 그대로 open() 한다.
# ---------------------------------------------------------------------------
@dsl.component(base_image="python:3.12-slim")
def consume_from_fuse(file_path: str) -> int:
    with open(file_path) as f:
        lines = [line for line in f.read().splitlines() if line]

    num_rows = max(len(lines) - 1, 0)  # 헤더 제외
    print(f"[consume] read {num_rows} rows from FUSE path: {file_path}")
    return num_rows


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
@dsl.pipeline(
    name="data-sharing-gcs-fuse",
    description="GCS Fuse 마운트(/gcs/<bucket>/...)로 데이터를 공유하는 예제",
)
def gcs_fuse_pipeline(
    bucket: str,
    file_name: str = "02-data-sharing/gcs-fuse/sample.csv",
):
    produce_task = produce_to_fuse(bucket=bucket, file_name=file_name)
    consume_from_fuse(file_path=produce_task.output)


if __name__ == "__main__":
    output_path = Path(__file__).parent / "gcs-fuse.yaml"
    compiler.Compiler().compile(
        pipeline_func=gcs_fuse_pipeline,
        package_path=str(output_path),
    )
