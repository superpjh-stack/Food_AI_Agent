# GitHub Repository Secrets Setup Guide

이 가이드는 `infra/gcloud-setup.sh` 실행 후 GitHub Actions CI/CD를 위한 시크릿 설정 방법을 안내합니다.

---

## Prerequisites

- `infra/gcloud-setup.sh` 스크립트가 성공적으로 완료되었을 것
- GitHub Repository에 Admin 권한이 있을 것
- `gcloud` CLI가 인증된 상태일 것

---

## 1. Secrets vs Environment Secrets 구분

| 구분 | 적용 범위 | 용도 |
|---|---|---|
| **Repository Secrets** | 모든 워크플로우 | WIF 설정, 프로젝트 공통 값 |
| **Environment Secrets** | 특정 환경(staging/production)만 | API 키, 환경별 설정 |

> Repository Secrets는 모든 브랜치/환경에서 접근 가능합니다.
> Environment Secrets는 해당 환경이 지정된 워크플로우 job에서만 접근됩니다.

---

## 2. Repository Secrets 설정

GitHub Repository > Settings > Secrets and variables > Actions > **New repository secret**

### `WIF_PROVIDER`

Workload Identity Federation Provider의 전체 리소스 이름입니다.

**값 확인 방법:**
```bash
gcloud iam workload-identity-pools providers describe github-provider \
  --workload-identity-pool=github-pool \
  --location=global \
  --format="value(name)"
```

**출력 형식:**
```
projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider
```

이 전체 문자열을 `WIF_PROVIDER` 시크릿 값으로 설정합니다.

### `WIF_SA_EMAIL`

Cloud Run 서비스 계정 이메일입니다.

**값:**
```
food-ai-api-sa@food-ai-agent-prod.iam.gserviceaccount.com
```

> 프로젝트 ID가 다른 경우 `food-ai-agent-prod` 부분을 실제 프로젝트 ID로 변경하세요.

**Required IAM roles on this service account:**
- `roles/run.admin` — deploy to Cloud Run
- `roles/artifactregistry.writer` — push Docker images
- `roles/iam.serviceAccountUser` — act as Cloud Run service account
- `roles/cloudsql.client` — connect to Cloud SQL
- `roles/secretmanager.secretAccessor` — read Secret Manager secrets

### `GCP_PROJECT_ID`

```
food-ai-agent-prod
```

### `GCP_REGION`

```
asia-northeast3
```

### `CLOUD_SQL_CONNECTION`

Cloud SQL 인스턴스 연결 이름입니다.

**값 확인 방법:**
```bash
gcloud sql instances describe food-ai-agent-db \
  --format="value(connectionName)"
```

**출력 형식:**
```
food-ai-agent-prod:asia-northeast3:food-ai-agent-db
```

### `ANTHROPIC_API_KEY_TEST`

Anthropic API key used **only during CI test runs**. This can be a separate key with lower rate limits.

```
sk-ant-api03-...
```

> If tests mock AI calls, this can be a dummy value like `sk-ant-test-dummy`.

### `OPENAI_API_KEY_TEST`

OpenAI API key used **only during CI test runs** (for embedding calls in tests).

```
sk-...
```

> If embedding calls are mocked in tests, a dummy value suffices.

---

## 3. GitHub Environments 생성

GitHub Repository > Settings > Environments

### `staging` Environment

1. **New environment** 클릭 > 이름: `staging`
2. Protection rules:
   - **Required reviewers**: 설정 안 함 (자동 배포 허용)
   - **Wait timer**: 0분
3. Deployment branches: `develop`, `staging/*` 패턴 허용

### `production` Environment

1. **New environment** 클릭 > 이름: `production`
2. Protection rules:
   - **Required reviewers**: 1명 이상 지정 (팀 리드 또는 DevOps 담당자)
   - **Wait timer**: 5분 (실수 방지 대기)
3. Deployment branches: `main`, `master` 만 허용

---

## 4. Environment Secrets 설정

각 환경(staging / production)에 개별 설정합니다.

GitHub Repository > Settings > Environments > (환경 선택) > **Add secret**

### staging Environment Secrets

| Secret Name | 값 | 설명 |
|---|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-...` (테스트/스테이징용 키) | Claude API 키 |
| `OPENAI_API_KEY` | `sk-...` (테스트/스테이징용 키) | 임베딩용 OpenAI API 키 |

### production Environment Secrets

| Secret Name | 값 | 설명 |
|---|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-...` (프로덕션용 키) | Claude API 키 |
| `OPENAI_API_KEY` | `sk-...` (프로덕션용 키) | 임베딩용 OpenAI API 키 |

> staging과 production에서 별도의 API 키를 사용하여 비용과 사용량을 분리하세요.

### Cloud Run Secrets (via Secret Manager, NOT GitHub Secrets)

이 시크릿들은 GCP Secret Manager를 통해 Cloud Run에 런타임 주입됩니다 -- GitHub에 저장하지 않습니다:

| Secret Manager Name | Env Var | Description |
|---|---|---|
| `database-url` | `DATABASE_URL` | PostgreSQL connection string (Cloud SQL) |
| `jwt-secret` | `JWT_SECRET_KEY` | JWT signing key |
| `anthropic-api-key` | `ANTHROPIC_API_KEY` | Production Anthropic API key |
| `openai-api-key` | `OPENAI_API_KEY` | Production OpenAI API key |

---

## 5. 워크플로우에서의 사용 예시

```yaml
# .github/workflows/deploy-api.yml
name: Deploy API

on:
  push:
    branches: [main]
    paths: ['food-ai-agent-api/**']

permissions:
  contents: read
  id-token: write  # WIF OIDC 토큰 발급에 필요

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install & Test
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY_TEST }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY_TEST }}
        run: |
          cd food-ai-agent-api
          pip install -r requirements.txt
          pytest

  deploy:
    needs: test
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4

      - id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SA_EMAIL }}

      - uses: google-github-actions/setup-gcloud@v2

      - name: Build & Push Docker Image
        run: |
          gcloud auth configure-docker ${{ secrets.GCP_REGION }}-docker.pkg.dev --quiet
          docker build -t ${{ secrets.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/food-ai/api:${{ github.sha }} \
            -f food-ai-agent-api/Dockerfile food-ai-agent-api/
          docker push ${{ secrets.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/food-ai/api:${{ github.sha }}

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy food-ai-agent-api \
            --image=${{ secrets.GCP_REGION }}-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/food-ai/api:${{ github.sha }} \
            --region=${{ secrets.GCP_REGION }} \
            --quiet
```

---

## 6. Verification Steps (검증)

모든 시크릿 설정 후 아래 항목을 확인하세요.

### 6-1. Repository Secrets 확인

GitHub Repository > Settings > Secrets and variables > Actions 에서 다음 시크릿이 표시되는지 확인:

- [ ] `WIF_PROVIDER`
- [ ] `WIF_SA_EMAIL`
- [ ] `GCP_PROJECT_ID`
- [ ] `GCP_REGION`
- [ ] `CLOUD_SQL_CONNECTION`
- [ ] `ANTHROPIC_API_KEY_TEST`
- [ ] `OPENAI_API_KEY_TEST`

### 6-2. Environment Secrets 확인

각 환경 페이지에서 다음 시크릿이 표시되는지 확인:

**staging:**
- [ ] `ANTHROPIC_API_KEY`
- [ ] `OPENAI_API_KEY`

**production:**
- [ ] `ANTHROPIC_API_KEY`
- [ ] `OPENAI_API_KEY`

### 6-3. CLI 검증

```bash
# Repository secrets 목록 확인
gh secret list

# Environment secrets 확인
gh secret list --env staging
gh secret list --env production
```

### 6-4. WIF 연결 테스트

테스트 워크플로우를 수동 실행하여 WIF 인증이 정상 동작하는지 확인:

```yaml
# .github/workflows/test-wif.yml
name: Test WIF Auth

on: workflow_dispatch

permissions:
  contents: read
  id-token: write

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SA_EMAIL }}

      - uses: google-github-actions/setup-gcloud@v2

      - name: Verify
        run: |
          echo "Authenticated as:"
          gcloud auth list
          echo "Project:"
          gcloud config get-value project
```

### 6-5. Environment Protection 확인

1. `production` 환경에 Required reviewer가 설정되어 있는지 확인
2. `production` 환경의 Deployment branches가 `main`/`master`로 제한되어 있는지 확인
3. 테스트 PR을 `main`에 머지하여 배포 워크플로우가 reviewer 승인을 대기하는지 확인

---

## Troubleshooting

### "Error: google-github-actions/auth failed"

- `WIF_PROVIDER` 값이 전체 리소스 경로인지 확인 (`projects/NUMBER/locations/global/...` 형식)
- GitHub repo 이름이 WIF provider의 `attribute-condition`과 일치하는지 확인:
  ```bash
  gcloud iam workload-identity-pools providers describe github-provider \
    --workload-identity-pool=github-pool \
    --location=global \
    --format="yaml(attributeCondition)"
  ```
- 워크플로우에 `permissions.id-token: write`가 설정되어 있는지 확인

### "Permission denied" on Artifact Registry

- `WIF_SA_EMAIL`의 SA에 `roles/artifactregistry.writer`가 부여되어 있는지 확인
- Repository `food-ai`가 `asia-northeast3`에 존재하는지 확인:
  ```bash
  gcloud artifacts repositories list --location=asia-northeast3
  ```

### "Permission denied" on Cloud Run deploy

- SA에 `roles/run.admin`과 `roles/iam.serviceAccountUser`가 부여되어 있는지 확인:
  ```bash
  gcloud projects get-iam-policy food-ai-agent-prod \
    --flatten="bindings[].members" \
    --filter="bindings.members:food-ai-api-sa@" \
    --format="table(bindings.role)"
  ```

### Secret 접근 실패: "Permission denied on secret"

- Cloud Run SA에 `roles/secretmanager.secretAccessor`가 있는지 확인
- Secret이 존재하고 최소 1개의 활성 버전이 있는지 확인:
  ```bash
  gcloud secrets versions list database-url
  ```

### Tests fail with API key errors

- If tests mock AI calls, set `ANTHROPIC_API_KEY_TEST=sk-ant-test-dummy`
- If tests make real API calls, use valid keys with sufficient quota
