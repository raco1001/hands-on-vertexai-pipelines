# 핸즈온 참가자 가이드 — Fork 해서 따라 하기

이 리포를 fork 한 뒤 본인의 GCP 프로젝트로 챕터 01–03 을 직접 실행해보고 싶을 때 보는 문서입니다. 핵심 원칙은 **"GCP 리소스(서비스 계정, 버킷, WIF 풀)는 각자 본인 프로젝트에 만들고, 본인이 fork 한 repo 에 연결한다"** 는 것입니다.

원본 작성자의 프로젝트(`test-gcp-490616` 등) 와는 무관하게 동작하도록 모든 리소스를 본인 명의로 새로 만든다고 생각하시면 됩니다.

## 사전 준비물 (한 번만)

핸즈온 시작 전에 갖춰져 있어야 하는 것들:

- 본인 명의의 **GCP 프로젝트** (결제 계정 연결됨, 무료 크레딧으로도 충분)
- **GitHub 계정**
- 로컬에 **gcloud CLI**, **git**, **Python 3.12+**, **uv** 설치
- (챕터 03 까지 진행할 거면) 로컬에 **Docker** 가 깔려 있으면 사전 검증이 편함 (필수는 아님)

gcloud CLI 가 없으면:

```bash
brew install --cask google-cloud-sdk
source "$(brew --prefix)/share/google-cloud-sdk/path.zsh.inc"
gcloud --version
```

uv 가 없으면 [astral.sh/uv](https://docs.astral.sh/uv/) 에서 설치.

## 1단계 — Fork 와 로컬 클론

GitHub 의 원본 repo 페이지에서 **Fork** 버튼을 눌러 본인 계정으로 복제하시고, 로컬로 가져옵니다.

```bash
git clone git@github.com:<YOUR_USERNAME>/<FORK_NAME>.git
cd <FORK_NAME>
uv sync
```

`uv sync` 가 `pyproject.toml` / `uv.lock` 기준으로 가상환경을 만들고 의존성을 설치합니다.

## 2단계 — GCP 프로젝트 기초 설정

이 부분은 모두에게 공통입니다. 본인 프로젝트 ID 를 변수로 한 번 잡아두면 이후 명령이 깔끔합니다.

```bash
export PROJECT_ID=<your-gcp-project-id>
export REGION=us-central1
export BUCKET=${PROJECT_ID}-vertex-pipelines
```

### 2-1. 로그인 두 종류 + 프로젝트 / 쿼터 프로젝트 지정

gcloud CLI 와 Python SDK 가 쓰는 인증 경로가 달라서 둘 다 필요합니다.

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project $PROJECT_ID
gcloud auth application-default set-quota-project $PROJECT_ID
```

### 2-2. 필요한 API 한 번에 활성화

Vertex AI, Storage, IAM, Artifact Registry, Compute 까지.

```bash
gcloud services enable \
    aiplatform.googleapis.com \
    storage.googleapis.com \
    compute.googleapis.com \
    iamcredentials.googleapis.com \
    iam.googleapis.com \
    artifactregistry.googleapis.com \
    --project $PROJECT_ID
```

### 2-3. Pipeline root 버킷 생성

```bash
gcloud storage buckets create gs://$BUCKET --location=$REGION --project $PROJECT_ID
```

### 2-4. 기본 Compute Engine SA 에 버킷 권한 부여 (이거 안 하면 첫 실행에서 무조건 막힘)

Vertex AI Pipelines 는 파이프라인을 제출하는 사용자 권한이 아니라, **별도의 실행 SA** 로 GCS 에 접근합니다. 별도 지정 안 하면 기본 Compute Engine SA(`<PROJECT_NUMBER>-compute@developer.gserviceaccount.com`) 가 자동 선택됩니다. 이 SA 가 버킷 권한을 갖고 있어야 합니다.

```bash
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

gcloud storage buckets add-iam-policy-binding gs://$BUCKET \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/storage.objectAdmin" \
    --project $PROJECT_ID
```

자세한 배경은 `SETUP.md` 를 참고하세요.

## 3단계 — 환경변수 export

각 챕터 스크립트가 읽는 세 개를 셸에 잡아둡니다. `~/.zshrc` 에 박아둬도 됩니다.

```bash
export GCP_PROJECT=$PROJECT_ID
export GCP_REGION=$REGION
export PIPELINE_ROOT=gs://$BUCKET/pipeline-root
```

## 4단계 — 챕터 01 실행

가장 빠른 검증은 한 방에 컴파일 + 제출되는 direct-run 입니다.

```bash
uv run python 01-first-pipeline/01-direct-run.py
```

성공하면 콘솔 URL 이 출력됩니다. 그 URL 로 들어가서 **`generate-data → process-data → notify`** 가 차례로 도는 것을 확인합니다 (총 5–7 분 정도).

컴파일과 제출을 분리해서 보고 싶으면:

```bash
uv run python 01-first-pipeline/01-first-pipeline.py
uv run python submit.py \
    --project $GCP_PROJECT --region $GCP_REGION \
    --pipeline-root $PIPELINE_ROOT \
    --template 01-first-pipeline/first-pipeline.yaml
```

자세한 챕터별 설명은 `01-first-pipeline/README.md` 참고.

## 5단계 — 챕터 02 실행

세 가지 데이터 공유 방식을 각각 컴파일하고 제출합니다.

```bash
# 컴파일
uv run python 02-data-sharing/02-gcs-string.py
uv run python 02-data-sharing/02-artifact-io.py
uv run python 02-data-sharing/02-gcs-fuse.py

# 제출 (gcs-string / gcs-fuse 는 bucket 파라미터 필요)
uv run python submit.py --project $GCP_PROJECT --region $GCP_REGION \
    --pipeline-root $PIPELINE_ROOT \
    --template 02-data-sharing/gcs-string.yaml \
    --param bucket=$BUCKET

uv run python submit.py --project $GCP_PROJECT --region $GCP_REGION \
    --pipeline-root $PIPELINE_ROOT \
    --template 02-data-sharing/artifact-io.yaml

uv run python submit.py --project $GCP_PROJECT --region $GCP_REGION \
    --pipeline-root $PIPELINE_ROOT \
    --template 02-data-sharing/gcs-fuse.yaml \
    --param bucket=$BUCKET
```

각 파이프라인이 콘솔에서 어떻게 다르게 보이는지 비교합니다. 특히 `artifact-io` 의 Artifacts 탭에 metadata 가 노출되는 것과, `gcs-string` / `gcs-fuse` 는 그 탭이 비어 있고 Parameters 탭에 경로만 있는 것을 직접 확인하세요. 자세한 비교는 `02-data-sharing/README.md`.

## 6단계 — 챕터 03 (CI/CD) 셋업

여기가 본격적입니다. 본인 fork 의 워크플로우가 본인 GCP 프로젝트로 이미지를 푸시하고 파이프라인을 제출하도록 연결해야 합니다. 모든 명령은 위에서 잡은 `$PROJECT_ID`, `$REGION`, `$BUCKET`, `$PROJECT_NUMBER` 변수를 그대로 씁니다.

추가로 본인의 fork 정보를 변수로 잡으세요.

```bash
export GH_OWNER=<your-github-username>
export GH_REPO=<your-fork-name>
```

### 6-1. CI 전용 서비스 계정 생성

```bash
gcloud iam service-accounts create vertex-ci \
    --display-name "Vertex AI CI runner" \
    --project $PROJECT_ID

export CI_SA=vertex-ci@$PROJECT_ID.iam.gserviceaccount.com
```

### 6-2. SA 에 필요한 역할 부여

```bash
for role in \
    roles/aiplatform.user \
    roles/artifactregistry.writer \
    roles/storage.admin \
    roles/iam.serviceAccountUser
do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
      --member="serviceAccount:$CI_SA" --role="$role"
done

# Pipeline root 버킷에서도 객체 R/W 권한을 명시적으로 부여
gcloud storage buckets add-iam-policy-binding gs://$BUCKET \
    --member="serviceAccount:$CI_SA" \
    --role="roles/storage.objectAdmin" \
    --project $PROJECT_ID
```

### 6-3. Docker 이미지를 저장할 Artifact Registry 저장소 생성

신규 프로젝트는 GCR 가 비활성이라 **Artifact Registry 사용을 권장** 합니다. 현재 워크플로우의 기본은 `gcr.io` 로 되어 있으므로, AR 로 가려면 두 군데를 바꿔야 합니다 (자세한 변경 가이드는 `03-ci-cd/README.md` 의 마지막 절 참고):

1. `03-ci-cd/pipeline.py` 의 `IMAGE_REGISTRY` 기본값을 `${REGION}-docker.pkg.dev/${PROJECT_ID}/vertex-ci-images` 형태로
2. `.github/workflows/03-ci-cd.yml` 의 `gcloud auth configure-docker gcr.io` → `${REGION}-docker.pkg.dev` 도메인으로

저장소 생성:

```bash
gcloud artifacts repositories create vertex-ci-images \
    --repository-format=docker \
    --location=$REGION \
    --description="CI/CD images for Vertex AI pipelines" \
    --project $PROJECT_ID
```

### 6-4. Workload Identity Federation — 풀과 GitHub Provider 생성

서비스 계정 키 JSON 을 GitHub 시크릿에 올리지 않고, GitHub 가 발급하는 OIDC 토큰으로 GCP 인증하는 방식입니다.

```bash
# 1) Pool 생성
gcloud iam workload-identity-pools create github \
    --location=global \
    --display-name="GitHub Actions" \
    --project $PROJECT_ID

# 2) GitHub OIDC Provider 등록
gcloud iam workload-identity-pools providers create-oidc github-provider \
    --location=global \
    --workload-identity-pool=github \
    --display-name="GitHub OIDC" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
    --attribute-condition="assertion.repository_owner == '${GH_OWNER}'" \
    --project $PROJECT_ID
```

`attribute-condition` 의 `repository_owner == '${GH_OWNER}'` 가 핵심 보안 장치입니다. 이게 없으면 같은 issuer 의 다른 GitHub 사용자도 토큰으로 GCP 에 들어올 수 있습니다.

### 6-5. 본인 fork repo 가 SA 를 impersonate 할 수 있도록 바인딩

```bash
gcloud iam service-accounts add-iam-policy-binding $CI_SA \
    --role=roles/iam.workloadIdentityUser \
    --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github/attribute.repository/${GH_OWNER}/${GH_REPO}" \
    --project $PROJECT_ID
```

이 한 줄이 "이 SA 는 **이 특정 GitHub repo** 의 워크플로우에서만 impersonate 가능하다" 를 박는 부분입니다.

### 6-6. WIF Provider 의 전체 리소스 경로 확인

GitHub Variables 에 넣을 값입니다.

```bash
echo "projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github/providers/github-provider"
```

## 7단계 — GitHub repo Variables 등록

본인 fork 의 GitHub 페이지로 가서 **Settings → Secrets and variables → Actions → Variables** 탭에서 5 개 추가합니다 (Secrets 가 아니라 Variables).

| 이름 | 값 (예시) |
|---|---|
| `GCP_PROJECT` | `your-gcp-project-id` |
| `GCP_REGION` | `us-central1` |
| `PIPELINE_ROOT` | `gs://<your-project>-vertex-pipelines/pipeline-root` |
| `WIF_PROVIDER` | 6-6 명령이 출력한 전체 경로 |
| `WIF_SERVICE_ACCOUNT` | `vertex-ci@<your-project>.iam.gserviceaccount.com` |

## 8단계 — 첫 워크플로우 트리거

`main` 으로 빈 커밋을 한 번 푸시하면 워크플로우가 자동으로 실행됩니다.

```bash
git commit --allow-empty -m "trigger ci"
git push origin main
```

또는 GitHub repo 의 **Actions** 탭 → `03-ci-cd` 워크플로우 → **Run workflow** 버튼으로 수동 실행도 가능합니다.

## 9단계 — 결과 확인

Actions 탭에서 흐름이 이렇게 진행되는 것을 봅니다:

1. `Authenticate to Google Cloud (WIF)` — 통과 못 하면 6-4/6-5 의 WIF 바인딩이 잘못된 것
2. `Build & push each component image` — 통과 못 하면 6-3 의 Artifact Registry 또는 SA 의 `roles/artifactregistry.writer` 권한 누락
3. `Compile pipeline` — `IMAGE_TAG` 가 SHA 로 잘 박혔는지 로그 확인
4. `Submit pipeline to Vertex AI` — 통과하면 `console.cloud.google.com/vertex-ai/...` URL 이 출력됨

URL 클릭해서 Vertex AI 콘솔에서 `data-preparation → train → evaluation` 이 도는 것 확인. 첫 실행은 이미지 pull + CIFAR-10 다운로드까지 포함되어 15–20 분 정도 걸립니다. 두 번째부터는 캐싱으로 훨씬 빨라집니다.

## 자주 막히는 지점 모음

**`storage.objects.get` / `create` 권한 에러**
2단계 후반부에서 SA 에 버킷 권한 줬어도, 파이프라인 실행 SA (기본 Compute SA) 에도 따로 줘야 합니다. `gcloud storage buckets add-iam-policy-binding` 명령을 빼먹지 않았는지 확인.

**`Permission 'iam.serviceAccounts.getAccessToken' denied`**
WIF principalSet 의 `${GH_OWNER}/${GH_REPO}` 가 본인 fork 와 정확히 일치하지 않으면 발생. 대소문자, 오타, 그리고 **fork 한 계정 vs 원본 계정** 을 혼동하지 않았는지 확인.

**이미지 pull 실패 (`ErrImagePull` / `Schema 1 deprecated`)**
챕터 01 의 busybox 처럼 manifest 가 deprecated 된 외부 이미지 참조 시 발생. 본인이 빌드한 이미지를 쓰면 이 문제는 안 생깁니다. 챕터 03 은 본인 빌드 이미지만 쓰니 안전.

**`Invalid image URI` (Vertex AI 제출 단계)**
이미지 호스트가 Vertex AI 의 허용 목록에 없을 때 발생. `gcr.io/<project>`, `*-docker.pkg.dev/<project>`, Docker Hub (`busybox:stable` 같이 prefix 없는 형식) 만 허용됩니다.

**GPU 쿼터 0 으로 학습 실패**
A100 같은 상위 GPU 는 신규 프로젝트에서 0 으로 시작합니다. T4 는 1 까지 허용. `SETUP.md` 의 GPU 쿼터 확인 절 참고. 챕터 03 의 train 컴포넌트는 기본 CPU 학습이니 우선 그대로 돌려도 됩니다.

**워크플로우는 도는데 Vertex AI 콘솔에 파이프라인이 안 보임**
프로젝트가 일치하는지, 리전 셀렉터를 `us-central1` 로 두었는지 확인. 콘솔 좌측 상단의 프로젝트 선택과 좌측 메뉴의 리전을 둘 다 봐야 합니다.

**캐시가 없는데도 두 번째 실행이 너무 빠름**
KFP 가 입력이 같으면 캐시된 결과를 재사용합니다. 본인이 의도한 바가 아니면 워크플로우의 `--enable-caching` 옵션을 빼고 다시 푸시하세요.

## 정리 / 다음 단계

여기까지 통과하면 핸즈온의 모든 챕터를 본인 환경에서 재현한 것입니다. 다음으로 시도해 볼 만한 것들:

- **GPU 학습 활성화**: `03-ci-cd/pipeline.py` 의 `set_accelerator_*` 두 줄 주석 해제 + `train/Dockerfile` 의 base 를 CUDA 런타임으로 교체. T4 1 개로 충분.
- **하이퍼파라미터 변경 후 재배포**: `epochs`, `batch_size`, `lr` 을 `--param` 으로 오버라이드하거나, `pipeline.py` 의 기본값을 바꿔 커밋 → 자동 재배포.
- **컴포넌트 추가**: `inference` 컴포넌트를 추가해 모델을 받아서 단일 이미지에 대한 예측을 출력하도록 확장. 새 폴더만 만들면 워크플로우가 자동으로 인식해 빌드.
- **PR 트리거 추가**: 현재는 main push 에만 트리거. PR 에서 빌드까지만 하고 제출은 main 에서만 하도록 분리하면 더 안전한 GitOps 패턴이 됩니다.
