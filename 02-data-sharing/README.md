# 02 - 컴포넌트 간 데이터 공유

파이프라인이라는 건 결국 "한 컴포넌트의 결과물이 다음 컴포넌트의 입력이 되는" 일의 반복입니다. 그래서 **컴포넌트들 사이에서 데이터를 어떻게 주고받을 것인지** 는 KFP 를 배울 때 가장 먼저 확실히 이해하고 넘어가야 하는 주제입니다. 이 챕터는 같은 목표("앞 컴포넌트가 만든 CSV 를 뒤 컴포넌트가 읽어서 사용")를 **세 가지 서로 다른 방식** 으로 구현해서, 각 방식이 실제 어떻게 동작하는지 그리고 장단점이 무엇인지를 비교해볼 수 있도록 구성했습니다.

세 파이프라인 모두 **컴파일만** 합니다. 즉, `.yaml` 파일을 만들어 주지 서버에 제출하지는 않습니다. 제출은 루트의 `submit.py` 에 템플릿 경로와 파라미터를 넘겨 직접 수행합니다.

## 세 가지 방식의 개요

**첫 번째 방식 (`02-gcs-string.py`) 은 GCS URI 문자열을 그대로 주고받는 방식** 입니다. 데이터 생성 컴포넌트는 파일을 `gs://bucket/path` 에 업로드한 뒤 그 URI 문자열을 `str` 타입 출력으로 리턴합니다. 데이터 활용 컴포넌트는 `str` 입력으로 그 URI 를 받아 `google-cloud-storage` 클라이언트로 직접 다운로드해서 사용합니다. 컴포넌트 시그니처가 문자열로만 구성되기 때문에 코드가 매우 투명하고, 저장 위치를 컴포넌트가 직접 통제할 수 있습니다. 반대로 KFP 입장에서는 이 문자열이 "그냥 문자열" 이기 때문에 Vertex AI UI 에서 아티팩트로 인식되지 않고, lineage(어떤 실행의 어떤 산출물이 어디로 이어졌는지) 추적도 되지 않습니다. 외부 시스템과 경로를 주고받아야 하거나, 이미 있는 파일을 참조로 넘겨야 할 때 적합합니다.

**두 번째 방식 (`02-artifact-io.py`) 은 KFP 아티팩트 타입으로 주고받는 방식** 입니다. `Output[Dataset]`, `Input[Dataset]` 을 사용합니다. 생성 컴포넌트는 `output_dataset.path` 라는 로컬 경로처럼 보이는 곳에 파일을 쓰고, 소비 컴포넌트는 `input_dataset.path` 로 읽습니다. 실제 저장 위치는 KFP 가 자동으로 `pipeline-root` 아래의 고유한 GCS 경로로 매핑하고, 아티팩트 metadata(행 수, 포맷 등)도 함께 저장됩니다. 이 방식이 **KFP 의 기본 권장 패턴** 입니다. Vertex AI UI 에서 각 컴포넌트의 출력 아티팩트를 확인할 수 있고, lineage 가 자동으로 추적되며, 재실행 시 캐싱도 잘 동작합니다. 단점은 컴포넌트가 저장 경로를 직접 정할 수 없다는 점인데, 대부분의 경우에는 오히려 그 편이 좋습니다.

**세 번째 방식 (`02-gcs-fuse.py`) 은 GCS Fuse 마운트를 활용하는 방식** 입니다. Vertex AI Pipelines 의 각 컴포넌트 컨테이너에는 프로젝트에서 접근 가능한 **모든 GCS 버킷이 `/gcs/<bucket>/...` 경로에 Cloud Storage FUSE 로 자동 마운트** 됩니다. 별도 설정이 필요 없습니다. 그래서 이 방식에서는 컴포넌트가 그냥 `open("/gcs/my-bucket/path/to/file")` 처럼 일반 파일처럼 읽고 쓰면, 내부적으로 GCS 와 동기화됩니다. 대용량 파일을 스트리밍으로 처리하거나, 기존에 로컬 파일을 가정하고 짜여진 코드를 GCS 와 연결하고 싶을 때 매우 유용합니다. 대신 FUSE 는 POSIX 를 완전히 지원하지는 않습니다. 랜덤 쓰기, 원자적 rename, 디렉터리 의미론 등에서 제한이 있어, **읽기 중심이나 한 번에 전체 파일을 쓰는 워크로드에 적합** 합니다.

## 어떤 방식을 언제 쓰는가

기본은 **KFP 아티팩트 방식** 입니다. Vertex AI 의 관리 기능(아티팩트 UI, lineage, 캐싱)을 모두 활용할 수 있고, 컴포넌트 간 결합도도 낮습니다. 이후 챕터 03 도 이 방식을 사용합니다.

**GCS URI 문자열 방식** 은 외부에서 이미 만들어진 파일을 가리켜야 하거나, 파이프라인 외부 도구(BigQuery export 등) 와 경로를 교환해야 할 때 씁니다. 예를 들어 DA 팀이 매일 특정 경로에 떨어뜨려 놓는 CSV 를 읽어오는 전처리 컴포넌트라면 이 방식이 자연스럽습니다.

**GCS Fuse 방식** 은 학습/추론 컴포넌트가 대용량 체크포인트나 이미지 데이터를 파일시스템처럼 스트리밍으로 다룰 때 적합합니다. 또는 코드베이스가 이미 로컬 경로 기준으로 짜여져 있어서 최소 수정으로 GCS 에 붙이고 싶을 때 빠른 해결책이 됩니다.

## 컴파일 방법

세 파일 모두 `if __name__ == "__main__"` 에서 같은 폴더에 YAML 을 생성합니다. 한 번에 모두 컴파일하려면 아래 세 줄을 순서대로 실행하면 됩니다.

```bash
uv run python 02-data-sharing/02-gcs-string.py
uv run python 02-data-sharing/02-artifact-io.py
uv run python 02-data-sharing/02-gcs-fuse.py
```

그러면 각각 `gcs-string.yaml`, `artifact-io.yaml`, `gcs-fuse.yaml` 이 생깁니다. 이 YAML 들을 루트 `submit.py` 로 넘기면 됩니다.

## 제출 방법

공통으로 아래 값들이 필요합니다. 본인 환경에 맞춰 바꿔 쓰세요.

```bash
PROJECT=my-gcp-project
REGION=us-central1
ROOT=gs://my-bucket/pipeline-root
BUCKET=my-bucket   # 실제 쓰기 권한이 있는 버킷 이름 (gs:// 없이)
```

**GCS 문자열 파이프라인** 은 `bucket` 파라미터가 필수입니다. 이 버킷의 `blob_name` 경로(기본값 `02-data-sharing/gcs-string/sample.csv`) 에 파일이 업로드되고, 다음 컴포넌트가 그 URI 를 받아 다시 읽어 들입니다.

```bash
uv run python submit.py \
    --project $PROJECT --region $REGION --pipeline-root $ROOT \
    --template 02-data-sharing/gcs-string.yaml \
    --param bucket=$BUCKET
```

**아티팩트 파이프라인** 은 별도 버킷 파라미터가 필요 없습니다. 저장 위치를 KFP 가 `pipeline-root` 아래로 자동 지정하기 때문입니다. `num_rows` 만 오버라이드할 수 있습니다.

```bash
uv run python submit.py \
    --project $PROJECT --region $REGION --pipeline-root $ROOT \
    --template 02-data-sharing/artifact-io.yaml \
    --param num_rows=50
```

**GCS Fuse 파이프라인** 은 FUSE 로 실제 파일이 쓰여질 버킷이 필요하므로 `bucket` 을 넘깁니다. 내부적으로 `/gcs/<bucket>/<file_name>` 경로에 파일을 쓰는데, 이건 자동으로 `gs://<bucket>/<file_name>` 에 저장됩니다.

```bash
uv run python submit.py \
    --project $PROJECT --region $REGION --pipeline-root $ROOT \
    --template 02-data-sharing/gcs-fuse.yaml \
    --param bucket=$BUCKET
```

## 돌린 뒤 어디서 결과를 확인하는가

세 파이프라인 모두 제출 후 출력된 콘솔 URL 에서 실행 상태를 볼 수 있습니다. 다만 **아티팩트 방식** 만 UI 에서 각 컴포넌트의 입출력 아티팩트가 카드 형태로 노출됩니다. 해당 카드를 클릭하면 `num_rows`, `format` 같은 metadata 가 보이고, 저장된 실제 GCS 경로로도 이동할 수 있습니다. 다른 두 방식은 결과물이 GCS 에 파일로만 떨어지므로, 버킷을 직접 열어봐야 합니다.

## 권한 체크리스트

세 파이프라인이 공통으로 필요로 하는 것은 Vertex AI Pipelines 실행 권한(`roles/aiplatform.user`) 과 `pipeline-root` 버킷에 대한 `roles/storage.objectAdmin` 입니다. 여기에 더해 GCS 문자열 / GCS Fuse 파이프라인은 파이프라인 실행 서비스 계정이 **`bucket` 파라미터로 지정한 버킷** 에도 쓰기/읽기 권한을 가지고 있어야 합니다. `pipeline-root` 와 같은 버킷을 쓴다면 추가 설정은 필요 없고, 다른 버킷이라면 `roles/storage.objectAdmin` 을 추가로 부여해야 합니다.
