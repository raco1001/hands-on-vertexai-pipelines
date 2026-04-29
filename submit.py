"""컴파일된 KFP 파이프라인을 Vertex AI Pipelines 에 제출하는 스크립트.

인증: Application Default Credentials 를 사용한다. 최초 1회 로컬에서 실행:
    gcloud auth application-default login

사용법:
# 1) 원하는 파이프라인을 컴파일 (예: 01-first-pipeline/pipeline.py)
uv run python 01-first-pipeline/pipeline.py

# 2) 생성된 YAML 을 submit.py 로 제출
uv run python submit.py \
    --project my-gcp-project \
    --region us-central1 \
    --pipeline-root gs://my-bucket/pipeline-root \
    --template 01-first-pipeline/first-pipeline.yaml \
    --param num_rows=200 --param multiplier=5
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from google.cloud import aiplatform


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    # --- GCP 접속 정보 ---
    parser.add_argument("--project", required=True, help="GCP 프로젝트 ID")
    parser.add_argument(
        "--region", required=True, help="Vertex AI 리전 (예: us-central1)"
    )
    parser.add_argument(
        "--pipeline-root",
        required=True,
        help="파이프라인 산출물이 저장될 GCS 경로 (예: gs://bucket/path)",
    )

    # --- 파이프라인 템플릿 및 실행 옵션 ---
    parser.add_argument(
        "--template",
        required=True,
        help="컴파일된 파이프라인 YAML/JSON 파일 경로 (예: 01-first-pipeline/first-pipeline.yaml)",
    )
    parser.add_argument(
        "--display-name",
        default=None,
        help="PipelineJob 의 display name (미지정 시 자동 생성)",
    )
    parser.add_argument(
        "--service-account",
        default=None,
        help="파이프라인 실행 시 사용할 서비스 계정 이메일 (선택)",
    )
    parser.add_argument(
        "--network",
        default=None,
        help="파이프라인이 사용할 VPC 네트워크 (선택)",
    )
    parser.add_argument(
        "--enable-caching", action="store_true", help="스텝 캐싱 활성화"
    )
    parser.add_argument(
        "--sync", action="store_true", help="파이프라인 종료까지 블로킹 대기"
    )

    # --- 파이프라인 파라미터 ---
    # `--param KEY=VALUE` 를 여러 번 넘기면 parameter_values 로 전달된다.
    # VALUE 는 먼저 JSON 으로 파싱을 시도하고, 실패하면 문자열로 간주한다.
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="파이프라인 파라미터 (반복 지정 가능)",
    )

    return parser.parse_args()


def _parse_params(raw: list[str]) -> dict[str, object]:
    """`KEY=VALUE` 형식의 리스트를 dict 로 변환한다."""
    parsed: dict[str, object] = {}
    for entry in raw:
        key, sep, value = entry.partition("=")
        if not sep:
            raise SystemExit(f"--param 형식이 올바르지 않습니다: {entry!r} (KEY=VALUE)")
        try:
            parsed[key] = json.loads(value)
        except json.JSONDecodeError:
            parsed[key] = value
    return parsed


def main() -> None:
    args = parse_args()

    # aiplatform 초기화: 이후 생성되는 리소스들의 기본 project/region 설정
    aiplatform.init(
        project=args.project,
        location=args.region,
        staging_bucket=args.pipeline_root,
    )

    display_name = (
        args.display_name
        or f"pipeline-{datetime.now(UTC):%Y%m%d-%H%M%S}"
    )

    parameter_values = _parse_params(args.param)

    # PipelineJob: 컴파일된 템플릿 + 파라미터 값을 묶은 실행 단위
    job = aiplatform.PipelineJob(
        display_name=display_name,
        template_path=args.template,
        pipeline_root=args.pipeline_root,
        parameter_values=parameter_values or None,
        enable_caching=args.enable_caching,
    )

    # submit() 는 비동기 제출. 동기 대기가 필요하면 --sync 로 wait() 호출.
    job.submit(
        service_account=args.service_account,
        network=args.network,
    )

    print(f"제출 완료 PipelineJob: {job.resource_name}")
    print(f"콘솔 URL: {job._dashboard_uri()}")

    if args.sync:
        job.wait()
        print(f"최종 상태: {job.state}")


if __name__ == "__main__":
    main()
