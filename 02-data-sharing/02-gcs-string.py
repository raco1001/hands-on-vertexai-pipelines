"""GCS URI 문자열로 데이터를 공유하는 파이프라인.

- 컴포넌트는 string 으로 `gs://bucket/blob` 경로만 주고받는다.
- 실제 입출력은 각 컴포넌트가 google-cloud-storage 로 직접 처리한다.
- 장점: 구조가 단순, 컴포넌트 인터페이스가 투명.
- 단점: KFP 가 아티팩트로 인식하지 않아 lineage / metadata 추적이 안 된다.
"""

from pathlib import Path

from kfp import compiler, dsl


# ---------------------------------------------------------------------------
# 1) 데이터 생성 컴포넌트
#    - 주어진 버킷/블롭 경로에 CSV 텍스트를 업로드하고 URI 를 리턴한다.
# ---------------------------------------------------------------------------
@dsl.component(
    base_image="python:3.12-slim",
    packages_to_install=["google-cloud-storage==2.18.2"],
)
def produce_to_gcs(bucket: str, blob_name: str) -> str:
    from google.cloud import storage

    csv_text = "id,value\n1,10\n2,20\n3,30\n"

    client = storage.Client()
    blob = client.bucket(bucket).blob(blob_name)
    blob.upload_from_string(csv_text, content_type="text/csv")

    uri = f"gs://{bucket}/{blob_name}"
    print(f"[produce] uploaded to {uri}")
    return uri


# ---------------------------------------------------------------------------
# 2) 데이터 활용 컴포넌트
#    - 선행 컴포넌트가 리턴한 gs:// URI 를 받아 직접 다운로드해서 사용한다.
# ---------------------------------------------------------------------------
@dsl.component(
    base_image="python:3.12-slim",
    packages_to_install=["google-cloud-storage==2.18.2"],
)
def consume_from_gcs(gcs_uri: str) -> int:
    from google.cloud import storage

    assert gcs_uri.startswith("gs://"), f"invalid uri: {gcs_uri}"
    bucket_name, _, blob_name = gcs_uri.removeprefix("gs://").partition("/")

    client = storage.Client()
    content = client.bucket(bucket_name).blob(blob_name).download_as_text()

    lines = [line for line in content.splitlines() if line]
    num_rows = max(len(lines) - 1, 0)  # 헤더 제외
    print(f"[consume] read {num_rows} rows from {gcs_uri}")
    return num_rows


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
@dsl.pipeline(
    name="data-sharing-gcs-string",
    description="GCS URI 문자열로 데이터를 주고받는 예제",
)
def gcs_string_pipeline(
    bucket: str,
    blob_name: str = "02-data-sharing/gcs-string/sample.csv",
):
    produce_task = produce_to_gcs(bucket=bucket, blob_name=blob_name)
    consume_from_gcs(gcs_uri=produce_task.output)


if __name__ == "__main__":
    output_path = Path(__file__).parent / "gcs-string.yaml"
    compiler.Compiler().compile(
        pipeline_func=gcs_string_pipeline,
        package_path=str(output_path),
    )
