# 01 - 첫 Vertex AI 파이프라인

이 폴더는 KFP(Kubeflow Pipelines) SDK v2 로 파이프라인을 작성해 Google Cloud 의 Vertex AI Pipelines 위에서 실행하는 가장 기본적인 예제를 다룹니다. "파이프라인이란 결국 컴포넌트들을 연결한 DAG 이다" 라는 개념을 실제 코드로 확인하는 것이 이 단계의 목표입니다.

## 무엇을 배우는가

여기서는 컴포넌트를 정의하는 **두 가지 방식**과, 컴포넌트 간 실행 순서를 결정하는 **두 가지 방식**을 동시에 보여줍니다. 하나의 파이프라인 안에 이 네 가지 개념이 모두 들어가 있기 때문에, 이 코드 한 덩어리만 이해하면 이후 챕터가 훨씬 수월해집니다.

첫 번째 컴포넌트인 `generate_data` 는 Python 함수를 그대로 컴포넌트로 만드는 **함수형 컴포넌트** (`@dsl.component`) 입니다. 함수의 인자, 타입 힌트, 반환값이 그대로 컴포넌트의 인터페이스가 되고, 런타임에 필요한 pip 패키지는 `packages_to_install` 로 지정해서 실행 시 자동 설치됩니다. 새로운 의존성이 생겨도 Docker 이미지를 빌드할 필요가 없기 때문에 **실험/프로토타이핑 단계에 가장 빠릅니다.** 다만 실행할 때마다 pip install 이 일어나기 때문에 반복 실행 시에는 이미지 기반 컴포넌트보다 느립니다.

두 번째 컴포넌트인 `process_data` 는 이미 빌드되어 레지스트리에 올라가 있는 **prebuilt 컨테이너 이미지** 를 실행하는 `@dsl.container_component` 입니다. `dsl.ContainerSpec` 으로 이미지 URL, command, args 를 직접 지정합니다. 여기서는 `busybox` 이미지를 가져와서 `awk` 로 CSV 를 변환하는데, 실제 프로젝트에서는 팀에서 관리하는 학습/전처리 이미지를 여기에 넣게 됩니다. 이미지를 한 번만 빌드해 두면 이후 실행은 기동 시간이 짧고, 파이썬 외 언어/런타임도 자유롭게 쓸 수 있습니다. 이 방식의 비용은 이미지 빌드 파이프라인이 필요하다는 점인데, 그 부분은 챕터 03 에서 다룹니다.

세 번째 컴포넌트인 `notify` 는 단순히 메시지를 찍는 함수형 컴포넌트입니다. 이 컴포넌트는 앞 두 컴포넌트의 출력을 인자로 전혀 받지 않습니다. 그럼에도 불구하고 "`process_data` 가 성공한 뒤에만 실행되어야 한다" 라는 순서 제약이 필요한 경우가 있죠 (예: 알림, 로깅, 후처리). 이런 경우에 `.after()` 를 사용합니다. `notify(...).after(proc_task)` 한 줄로 인자 연결 없이 순서만 강제할 수 있습니다.

정리하면 선후관계를 만드는 방법은 두 가지입니다. **(1) 자동 추론** — 컴포넌트의 출력을 다른 컴포넌트의 입력으로 넘기면 KFP 가 dependency 그래프를 자동으로 만듭니다. 이 예제에서는 `gen_task.outputs["output_dataset"]` 를 `process_data` 의 `input_dataset` 인자로 넘겼기 때문에 `generate_data → process_data` 순서가 자동으로 정해집니다. **(2) 명시적 강제** — 인자 연결이 없지만 순서가 필요하면 `.after()` 로 직접 건다. 실제로는 (1) 을 기본으로 쓰고, 꼭 필요한 때만 (2) 를 씁니다.

## 폴더 구조와 각 파일의 역할

`01-first-pipeline.py` 는 파이프라인 정의와 함께 `if __name__ == "__main__"` 에서 YAML 로 컴파일만 수행합니다. 이 파일을 돌리면 같은 폴더에 `first-pipeline.yaml` 이 만들어지고, 그 YAML 을 루트의 `submit.py` 로 넘겨서 Vertex AI 에 제출하는 것이 "교과서적인" 흐름입니다.

`01-direct-run.py` 는 같은 파이프라인 정의에 더해 `submit_pipeline()` 함수를 내장하고 있고, `__main__` 에서 컴파일 직후 바로 그 함수를 호출합니다. `python 01-direct-run.py` 한 방에 "컴파일 + 제출" 이 끝나게 만든 편의 버전입니다. 여기서는 `project / region / pipeline_root` 를 환경변수(`GCP_PROJECT / GCP_REGION / PIPELINE_ROOT`) 로 읽습니다.

`first-pipeline.yaml` 은 컴파일 결과물입니다. 내용을 열어보면 IR(Intermediate Representation) YAML 인데, 파이프라인의 구조 · 컴포넌트 · 의존성이 선언적으로 들어가 있습니다. Vertex AI Pipelines 는 이 YAML 만 있으면 파이프라인을 재현할 수 있기 때문에, 이 YAML 을 아티팩트처럼 버전관리해두는 패턴도 많이 씁니다 (챕터 03 이 그런 패턴입니다).

## 실행 방법 A — 컴파일 따로, 제출 따로

가장 기본적인 흐름이고, 실무에서는 이 방식이 더 유연합니다. 컴파일된 YAML 하나로 파라미터만 바꿔가며 여러 번 제출할 수 있기 때문입니다.

먼저 컴파일합니다.

```bash
uv run python 01-first-pipeline/01-first-pipeline.py
```

그러면 `01-first-pipeline/first-pipeline.yaml` 이 생깁니다. 이어서 루트의 `submit.py` 에 GCP 접속 정보 3 가지(프로젝트, 리전, pipeline root 용 GCS 경로)와 템플릿 경로를 넘기면 제출됩니다. 파이프라인 파라미터는 `--param KEY=VALUE` 형태로 필요한 것만 오버라이드합니다.

```bash
uv run python submit.py \
    --project my-gcp-project \
    --region us-central1 \
    --pipeline-root gs://my-bucket/pipeline-root \
    --template 01-first-pipeline/first-pipeline.yaml \
    --param num_rows=200 \
    --param multiplier=5
```

제출이 성공하면 콘솔 URL 이 출력됩니다. 그 URL 을 브라우저에서 열면 실시간으로 그래프가 그려지고 각 컴포넌트 로그를 볼 수 있습니다.

## 실행 방법 B — 한 줄로 컴파일 + 제출

로컬에서 빠르게 돌려보고 싶을 때 편한 방법입니다. 먼저 환경변수 3개를 export 합니다.

```bash
export GCP_PROJECT=my-gcp-project
export GCP_REGION=us-central1
export PIPELINE_ROOT=gs://my-bucket/pipeline-root
```

그 다음 `01-direct-run.py` 만 실행하면 됩니다.

```bash
uv run python 01-first-pipeline/01-direct-run.py
```

이 파일은 내부적으로 먼저 `first-pipeline.yaml` 을 만들고, 이어서 `submit_pipeline()` 을 호출해 Vertex AI 에 제출합니다. 제출 함수는 비동기로 동작하기 때문에, 파이프라인이 완료될 때까지 기다리지 않고 제출 수락만 확인한 뒤 종료합니다. 자세한 실행 상태는 출력된 콘솔 URL 에서 확인하세요.

## 파이프라인 파라미터

이 파이프라인은 세 개의 파라미터를 받습니다. `num_rows` 는 `generate_data` 가 만드는 CSV 의 행 수로, 기본값은 100 입니다. `multiplier` 는 `process_data` 가 `value` 컬럼에 곱할 배수로 기본값은 3 입니다. `message` 는 `notify` 가 찍을 문자열로 기본값은 `"done"` 입니다. 모두 제출 시 `--param KEY=VALUE` 로 바꿀 수 있습니다.

## 사전 준비

이 챕터를 돌리려면 먼저 몇 가지가 준비되어 있어야 합니다. 첫째, 로컬에 `gcloud` CLI 가 설치되어 있어야 하고 `gcloud auth application-default login` 으로 ADC(Application Default Credentials) 가 세팅되어 있어야 합니다. Python 의 `google-cloud-aiplatform` SDK 는 이 ADC 로 인증합니다. 둘째, Vertex AI API 가 프로젝트에서 활성화되어 있어야 합니다(콘솔에서 한 번만 켜면 됩니다). 셋째, `PIPELINE_ROOT` 로 쓸 GCS 버킷이 미리 생성되어 있어야 하고, 로그인한 계정이 해당 버킷에 `roles/storage.objectAdmin` 권한을 가지고 있어야 합니다. 마지막으로 파이프라인 제출을 위해 `roles/aiplatform.user` 역할이 필요합니다.
