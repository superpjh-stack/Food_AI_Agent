# Food AI Agent - Deployment Runbook

> **Version**: 1.0.0
> **Last Updated**: 2026-02-25
> **Target**: Google Cloud Platform (asia-northeast3, Seoul)
> **Project ID**: `food-ai-agent-prod`

---

## Table of Contents

1. [전제조건 (Prerequisites)](#1-전제조건-prerequisites)
2. [최초 배포 순서 (First Deployment)](#2-최초-배포-순서-first-deployment)
3. [DB 마이그레이션 (Cloud SQL)](#3-db-마이그레이션-cloud-sql)
4. [pgvector 확장 활성화](#4-pgvector-확장-활성화)
5. [스모크 테스트 체크리스트](#5-스모크-테스트-체크리스트)
6. [일반 배포 프로세스 (Routine Deployment)](#6-일반-배포-프로세스-routine-deployment)
7. [롤백 절차 (Rollback)](#7-롤백-절차-rollback)
8. [모니터링](#8-모니터링)
9. [문제 해결 (Troubleshooting)](#9-문제-해결-troubleshooting)

---

## 1. 전제조건 (Prerequisites)

### 1.1 필수 도구 설치

| 도구 | 버전 | 설치 확인 |
|------|------|----------|
| gcloud CLI | 최신 | `gcloud version` |
| Docker | 24+ | `docker --version` |
| Python | 3.11+ | `python --version` |
| Cloud SQL Auth Proxy | 최신 | `cloud-sql-proxy --version` |
| gh (GitHub CLI) | 최신 | `gh --version` |

### 1.2 GCP 인증 및 프로젝트 설정

```bash
# Google Cloud 로그인
gcloud auth login

# 프로젝트 설정
gcloud config set project food-ai-agent-prod

# 리전 기본값 설정
gcloud config set run/region asia-northeast3
gcloud config set compute/region asia-northeast3

# Docker 인증 (Artifact Registry)
gcloud auth configure-docker asia-northeast3-docker.pkg.dev

# 현재 설정 확인
gcloud config list
```

### 1.3 필요 권한

작업자에게 다음 IAM 역할이 필요합니다:

| 역할 | 용도 |
|------|------|
| `roles/owner` 또는 `roles/editor` | 전체 리소스 관리 |
| `roles/run.admin` | Cloud Run 배포 |
| `roles/cloudsql.admin` | Cloud SQL 관리 |
| `roles/artifactregistry.admin` | Docker 이미지 관리 |
| `roles/secretmanager.admin` | 시크릿 생성/수정 |

### 1.4 관련 파일 위치

```
food-ai-agent-api/Dockerfile               # API 컨테이너 (multi-stage)
food-ai-agent-api/.env.example              # 환경변수 템플릿
food-ai-agent-api/alembic/                  # DB 마이그레이션
docker-compose.prod.yml                     # 로컬 프로덕션 테스트
.github/workflows/deploy-api.yml            # CI/CD 워크플로우
docs/infra/gcloud-architecture.md           # 아키텍처 상세
```

---

## 2. 최초 배포 순서 (First Deployment)

### Step 1: GCP 인프라 프로비저닝

`infra/gcloud-setup.sh` 스크립트를 실행하여 전체 인프라를 자동 프로비저닝합니다.

```bash
# 스크립트에 실행 권한 부여
chmod +x infra/gcloud-setup.sh

# 인프라 프로비저닝 실행 (약 15~20분 소요)
bash infra/gcloud-setup.sh
```

스크립트가 생성하는 리소스:
- GCP 프로젝트 API 활성화
- VPC 네트워크 (`food-ai-vpc`) + Private Services Access
- Serverless VPC Connector (`food-ai-connector`, 10.8.0.0/28)
- Cloud SQL PostgreSQL 16 인스턴스 (Staging + Production)
- Artifact Registry (`food-ai`)
- Cloud Run 서비스 계정
- Workload Identity Federation (GitHub Actions용)

### Step 2: Secret Manager에 실제 값 입력

```bash
# 1) DATABASE_URL (Cloud SQL Unix socket 형식)
#    Cloud SQL Private IP 확인 후 입력
CLOUD_SQL_IP=$(gcloud sql instances describe food-ai-db-prod \
  --format='value(ipAddresses[0].ipAddress)')
echo "Cloud SQL Private IP: $CLOUD_SQL_IP"

# Production DB URL
echo -n "postgresql+asyncpg://foodai_app:YOUR_STRONG_PASSWORD@/food_ai_agent?host=/cloudsql/food-ai-agent-prod:asia-northeast3:food-ai-db-prod" \
  | gcloud secrets create database-url --data-file=-

# Staging DB URL
echo -n "postgresql+asyncpg://foodai_app:YOUR_STRONG_PASSWORD@/food_ai_agent?host=/cloudsql/food-ai-agent-prod:asia-northeast3:food-ai-db-staging" \
  | gcloud secrets create database-url-staging --data-file=-

# 2) JWT Secret (자동 생성)
openssl rand -base64 64 | tr -d '\n' \
  | gcloud secrets create jwt-secret --data-file=-

# 3) Anthropic API Key
echo -n "sk-ant-YOUR_ANTHROPIC_KEY" \
  | gcloud secrets create anthropic-api-key --data-file=-

# 4) OpenAI API Key (임베딩용)
echo -n "sk-YOUR_OPENAI_KEY" \
  | gcloud secrets create openai-api-key --data-file=-

# 시크릿 목록 확인
gcloud secrets list

# 특정 시크릿 값 확인 (주의: 터미널에 출력됨)
gcloud secrets versions access latest --secret=database-url
```

**시크릿 값 업데이트** (이미 존재하는 시크릿):
```bash
echo -n "NEW_VALUE" | gcloud secrets versions add database-url --data-file=-
```

### Step 3: Cloud SQL pgvector 확장 활성화

```bash
# Cloud SQL Auth Proxy로 로컬에서 접속
cloud-sql-proxy food-ai-agent-prod:asia-northeast3:food-ai-db-prod &

# psql로 접속하여 pgvector 활성화
psql "host=127.0.0.1 port=5432 user=foodai_app dbname=food_ai_agent" <<EOF
CREATE EXTENSION IF NOT EXISTS vector;
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
EOF

# Proxy 종료
kill %1
```

자세한 내용은 [4. pgvector 확장 활성화](#4-pgvector-확장-활성화) 참조.

### Step 4: GitHub Secrets 설정

`infra/github-secrets-setup.md` 문서를 참조하여 GitHub Repository Secrets를 등록합니다.

```bash
# GitHub CLI로 Secrets 설정 (대안)
gh secret set WIF_PROVIDER --body "projects/NNNN/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
gh secret set WIF_SA_EMAIL --body "github-actions-sa@food-ai-agent-prod.iam.gserviceaccount.com"
gh secret set ANTHROPIC_API_KEY_TEST --body "sk-ant-test-key"
gh secret set OPENAI_API_KEY_TEST --body "sk-test-key"
```

GitHub Environments 설정 (GitHub UI):
- **staging**: 자동 배포 (main merge 시)
- **production**: Required reviewers 지정 (수동 승인)

### Step 5: 첫 Docker 이미지 빌드 및 Artifact Registry 푸시

```bash
# 로컬에서 Docker 이미지 빌드
docker build \
  -t asia-northeast3-docker.pkg.dev/food-ai-agent-prod/food-ai/food-ai-agent-api:v1.0.0 \
  -t asia-northeast3-docker.pkg.dev/food-ai-agent-prod/food-ai/food-ai-agent-api:latest \
  food-ai-agent-api/

# 빌드 결과 확인
docker images | grep food-ai-agent-api

# Artifact Registry에 푸시
docker push asia-northeast3-docker.pkg.dev/food-ai-agent-prod/food-ai/food-ai-agent-api:v1.0.0
docker push asia-northeast3-docker.pkg.dev/food-ai-agent-prod/food-ai/food-ai-agent-api:latest

# 푸시 확인
gcloud artifacts docker images list \
  asia-northeast3-docker.pkg.dev/food-ai-agent-prod/food-ai/food-ai-agent-api
```

### Step 6: 첫 Cloud Run 서비스 배포

```bash
# --- Staging 배포 ---
gcloud run deploy food-ai-agent-api-staging \
  --image=asia-northeast3-docker.pkg.dev/food-ai-agent-prod/food-ai/food-ai-agent-api:v1.0.0 \
  --region=asia-northeast3 \
  --platform=managed \
  --allow-unauthenticated \
  --add-cloudsql-instances=food-ai-agent-prod:asia-northeast3:food-ai-db-staging \
  --vpc-connector=food-ai-connector \
  --set-secrets="DATABASE_URL=database-url-staging:latest,JWT_SECRET_KEY=jwt-secret:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest,OPENAI_API_KEY=openai-api-key:latest" \
  --set-env-vars="APP_ENV=staging,DEBUG=false,CORS_ORIGINS=[\"https://staging.foodai.example.com\"],CLAUDE_MODEL=claude-sonnet-4-6,CLAUDE_MAX_TOKENS=4096,EMBEDDING_MODEL=text-embedding-3-small,EMBEDDING_DIMENSION=1536" \
  --min-instances=0 \
  --max-instances=5 \
  --cpu=2 \
  --memory=2Gi \
  --timeout=300 \
  --concurrency=80

# Staging URL 확인
STAGING_URL=$(gcloud run services describe food-ai-agent-api-staging \
  --region=asia-northeast3 --format='value(status.url)')
echo "Staging URL: $STAGING_URL"

# 스모크 테스트
curl -f "$STAGING_URL/health"

# --- Production 배포 ---
gcloud run deploy food-ai-agent-api \
  --image=asia-northeast3-docker.pkg.dev/food-ai-agent-prod/food-ai/food-ai-agent-api:v1.0.0 \
  --region=asia-northeast3 \
  --platform=managed \
  --allow-unauthenticated \
  --add-cloudsql-instances=food-ai-agent-prod:asia-northeast3:food-ai-db-prod \
  --vpc-connector=food-ai-connector \
  --set-secrets="DATABASE_URL=database-url:latest,JWT_SECRET_KEY=jwt-secret:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest,OPENAI_API_KEY=openai-api-key:latest" \
  --set-env-vars="APP_ENV=production,DEBUG=false,CORS_ORIGINS=[\"https://foodai.example.com\"],CLAUDE_MODEL=claude-sonnet-4-6,CLAUDE_MAX_TOKENS=4096,EMBEDDING_MODEL=text-embedding-3-small,EMBEDDING_DIMENSION=1536" \
  --min-instances=1 \
  --max-instances=10 \
  --cpu=2 \
  --memory=2Gi \
  --timeout=300 \
  --concurrency=80

# Production URL 확인
PROD_URL=$(gcloud run services describe food-ai-agent-api \
  --region=asia-northeast3 --format='value(status.url)')
echo "Production URL: $PROD_URL"
curl -f "$PROD_URL/health"
```

---

## 3. DB 마이그레이션 (Cloud SQL)

### 3.1 Cloud SQL Auth Proxy 설치 및 사용법

Cloud SQL Auth Proxy는 로컬 머신에서 Cloud SQL 인스턴스에 안전하게 접속할 수 있게 해줍니다.

```bash
# 설치 (Linux/macOS)
curl -o cloud-sql-proxy \
  https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.linux.amd64
chmod +x cloud-sql-proxy

# 설치 (Windows — WSL 또는 PowerShell)
# https://cloud.google.com/sql/docs/postgres/sql-proxy#install 에서 다운로드

# Proxy 시작 (백그라운드)
./cloud-sql-proxy food-ai-agent-prod:asia-northeast3:food-ai-db-prod &

# 접속 확인
psql "host=127.0.0.1 port=5432 user=foodai_app dbname=food_ai_agent"
```

### 3.2 로컬에서 원격 DB에 Alembic 마이그레이션 실행

```bash
# 1) Cloud SQL Auth Proxy 시작
./cloud-sql-proxy food-ai-agent-prod:asia-northeast3:food-ai-db-prod &

# 2) DATABASE_URL을 localhost로 설정하여 마이그레이션 실행
cd food-ai-agent-api

DATABASE_URL="postgresql+asyncpg://foodai_app:YOUR_PASSWORD@127.0.0.1:5432/food_ai_agent" \
  alembic -c alembic/alembic.ini upgrade head

# 3) 마이그레이션 상태 확인
DATABASE_URL="postgresql+asyncpg://foodai_app:YOUR_PASSWORD@127.0.0.1:5432/food_ai_agent" \
  alembic -c alembic/alembic.ini current

# 4) Proxy 종료
kill %1
```

### 3.3 Cloud Run Job으로 마이그레이션 실행 (권장)

운영 환경에서는 Cloud Run Job을 사용하여 마이그레이션을 실행하는 것을 권장합니다. VPC Connector를 통해 Cloud SQL에 직접 접속할 수 있으며, Secret Manager에서 자동으로 DB URL을 주입받습니다.

```bash
# Cloud Run Job 생성 (1회)
gcloud run jobs create food-ai-migrate \
  --image=asia-northeast3-docker.pkg.dev/food-ai-agent-prod/food-ai/food-ai-agent-api:latest \
  --region=asia-northeast3 \
  --add-cloudsql-instances=food-ai-agent-prod:asia-northeast3:food-ai-db-prod \
  --vpc-connector=food-ai-connector \
  --set-secrets="DATABASE_URL=database-url:latest" \
  --command="alembic" \
  --args="-c,alembic/alembic.ini,upgrade,head" \
  --max-retries=0 \
  --task-timeout=300s

# 마이그레이션 실행
gcloud run jobs execute food-ai-migrate --region=asia-northeast3 --wait

# 실행 로그 확인
gcloud run jobs executions list --job=food-ai-migrate --region=asia-northeast3
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=food-ai-migrate" \
  --limit=50 --format="table(timestamp,textPayload)"
```

**마이그레이션 실행 타이밍**:
- 새 마이그레이션 파일이 포함된 이미지를 Artifact Registry에 푸시한 후
- Cloud Run 서비스 배포 **전**에 실행
- CI/CD에서는 Build Job 이후, Deploy Job 이전에 배치

---

## 4. pgvector 확장 활성화

### 4.1 활성화 방법

Cloud SQL PostgreSQL 16은 pgvector를 네이티브로 지원합니다. 인스턴스 생성 시 `--database-flags=cloudsql.enable_pgvector=on` 플래그를 설정했다면, SQL 명령으로 확장만 활성화하면 됩니다.

```bash
# Cloud SQL Auth Proxy 시작
./cloud-sql-proxy food-ai-agent-prod:asia-northeast3:food-ai-db-prod &

# psql로 접속
psql "host=127.0.0.1 port=5432 user=foodai_app dbname=food_ai_agent"
```

```sql
-- pgvector 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;
```

### 4.2 확인 방법

```sql
-- 확장 설치 확인
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
-- 기대 결과: vector | 0.7.x

-- 벡터 컬럼이 있는 테이블 확인 (Alembic 마이그레이션 후)
SELECT table_name, column_name, udt_name
FROM information_schema.columns
WHERE udt_name = 'vector';

-- 벡터 인덱스 확인
SELECT indexname, indexdef
FROM pg_indexes
WHERE indexdef LIKE '%vector%' OR indexdef LIKE '%ivfflat%' OR indexdef LIKE '%hnsw%';
```

### 4.3 Staging DB에도 동일 적용

```bash
./cloud-sql-proxy food-ai-agent-prod:asia-northeast3:food-ai-db-staging --port=5433 &

psql "host=127.0.0.1 port=5433 user=foodai_app dbname=food_ai_agent" \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

## 5. 스모크 테스트 체크리스트

배포 후 아래 항목을 순서대로 확인합니다.

### 5.1 Health Check

```bash
# Cloud Run 서비스 URL 가져오기
URL=$(gcloud run services describe food-ai-agent-api \
  --region=asia-northeast3 --format='value(status.url)')

# Health check
curl -sf "$URL/health" | python -m json.tool
# 기대: {"status": "ok", ...}  HTTP 200
```

### 5.2 API Docs (Swagger UI)

```bash
# OpenAPI 문서 접근
curl -sf -o /dev/null -w "%{http_code}" "$URL/docs"
# 기대: 200

# 브라우저에서 확인
echo "API Docs: $URL/docs"
```

### 5.3 인증 (Auth)

```bash
# 토큰 발급 테스트
curl -sf -X POST "$URL/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=admin123" \
  | python -m json.tool
# 기대: {"access_token": "eyJ...", "token_type": "bearer"}

# 토큰 저장
TOKEN=$(curl -sf -X POST "$URL/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=admin123" \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### 5.4 AI Agent Chat

```bash
# AI 에이전트 채팅 테스트 (SSE 스트리밍)
curl -sf -N -X POST "$URL/api/v1/agent/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "오늘 식단 추천해줘", "site_id": "site-001"}' \
  --max-time 30
# 기대: SSE 이벤트 스트림 수신 (data: {...})
```

### 5.5 DB 연결 확인

```bash
# DB 상태가 health 엔드포인트에 포함되어 있지 않은 경우,
# API를 통해 간접 확인 (아이템 목록 조회 등)
curl -sf "$URL/api/v1/items?limit=1" \
  -H "Authorization: Bearer $TOKEN" \
  | python -m json.tool
# 기대: 200 OK (빈 리스트라도 정상 응답)
```

### 5.6 전체 체크리스트 요약

| # | 항목 | 엔드포인트 | 기대 결과 |
|---|------|-----------|----------|
| 1 | Health | `GET /health` | 200 OK |
| 2 | API Docs | `GET /docs` | 200 OK |
| 3 | Auth Token | `POST /api/v1/auth/token` | access_token 반환 |
| 4 | AI Chat | `POST /api/v1/agent/chat` | SSE 스트림 수신 |
| 5 | DB Query | `GET /api/v1/items` | 200 OK (JSON 응답) |
| 6 | pgvector | SQL: `SELECT extversion FROM pg_extension WHERE extname='vector'` | 0.7.x |

---

## 6. 일반 배포 프로세스 (Routine Deployment)

### 6.1 자동 배포 (GitHub Actions)

일반적인 배포는 `main` 브랜치에 push하면 자동으로 실행됩니다.

```
feature/* 브랜치에서 개발
  → PR 생성 (main 대상)
  → CI: pytest 52개 + lint (pgvector/pgvector:pg16 서비스 컨테이너)
  → PR 머지 (main)
  → Build: Docker 이미지 빌드 → Artifact Registry 푸시
  → Deploy Staging: 자동 배포 + 스모크 테스트 (/health)
  → [수동 승인] GitHub Environment "production" 승인
  → Deploy Production: 프로덕션 배포 + 검증
```

**워크플로우 파일**: `.github/workflows/deploy-api.yml`

### 6.2 배포 진행 모니터링

```bash
# GitHub Actions 실행 상태 확인
gh run list --workflow=deploy-api.yml --limit=5

# 특정 실행 상세 보기
gh run view <RUN_ID>

# 실행 로그 보기
gh run view <RUN_ID> --log
```

### 6.3 수동 배포 (긴급 시)

CI/CD를 거치지 않고 직접 배포해야 할 때:

```bash
# 1) 이미지 빌드 및 푸시
docker build \
  -t asia-northeast3-docker.pkg.dev/food-ai-agent-prod/food-ai/food-ai-agent-api:hotfix-$(date +%Y%m%d%H%M) \
  food-ai-agent-api/

docker push asia-northeast3-docker.pkg.dev/food-ai-agent-prod/food-ai/food-ai-agent-api:hotfix-$(date +%Y%m%d%H%M)

# 2) Cloud Run 배포 (새 revision 생성)
gcloud run deploy food-ai-agent-api \
  --image=asia-northeast3-docker.pkg.dev/food-ai-agent-prod/food-ai/food-ai-agent-api:hotfix-$(date +%Y%m%d%H%M) \
  --region=asia-northeast3

# 3) 배포 확인
gcloud run revisions list --service=food-ai-agent-api --region=asia-northeast3 --limit=5
```

### 6.4 Staging 환경에서 먼저 검증

프로덕션 배포 전 반드시 Staging에서 검증합니다:

```bash
# Staging 배포
gcloud run deploy food-ai-agent-api-staging \
  --image=asia-northeast3-docker.pkg.dev/food-ai-agent-prod/food-ai/food-ai-agent-api:latest \
  --region=asia-northeast3

# Staging 스모크 테스트
STAGING_URL=$(gcloud run services describe food-ai-agent-api-staging \
  --region=asia-northeast3 --format='value(status.url)')
curl -f "$STAGING_URL/health"
```

---

## 7. 롤백 절차 (Rollback)

### 7.1 Cloud Run Revision 롤백

Cloud Run은 모든 배포를 revision으로 관리합니다. 문제 발생 시 이전 revision으로 즉시 롤백할 수 있습니다.

```bash
# 현재 revision 목록 확인
gcloud run revisions list \
  --service=food-ai-agent-api \
  --region=asia-northeast3 \
  --limit=10

# 이전 revision으로 트래픽 100% 전환 (즉시 롤백)
gcloud run services update-traffic food-ai-agent-api \
  --to-revisions=food-ai-agent-api-00042-abc=100 \
  --region=asia-northeast3

# 롤백 확인
gcloud run services describe food-ai-agent-api \
  --region=asia-northeast3 \
  --format='value(status.traffic)'
```

**Canary 롤백** (점진적 트래픽 이동):

```bash
# 90% 이전 버전, 10% 새 버전
gcloud run services update-traffic food-ai-agent-api \
  --to-revisions=food-ai-agent-api-00042-abc=90,food-ai-agent-api-00043-def=10 \
  --region=asia-northeast3
```

### 7.2 DB 롤백 (Alembic Downgrade)

DB 스키마 변경을 롤백해야 할 경우:

```bash
# Cloud SQL Auth Proxy 시작
./cloud-sql-proxy food-ai-agent-prod:asia-northeast3:food-ai-db-prod &

cd food-ai-agent-api

# 현재 마이그레이션 버전 확인
DATABASE_URL="postgresql+asyncpg://foodai_app:PASSWORD@127.0.0.1:5432/food_ai_agent" \
  alembic -c alembic/alembic.ini current

# 한 단계 이전으로 롤백
DATABASE_URL="postgresql+asyncpg://foodai_app:PASSWORD@127.0.0.1:5432/food_ai_agent" \
  alembic -c alembic/alembic.ini downgrade -1

# 특정 revision으로 롤백
DATABASE_URL="postgresql+asyncpg://foodai_app:PASSWORD@127.0.0.1:5432/food_ai_agent" \
  alembic -c alembic/alembic.ini downgrade <REVISION_ID>

# Proxy 종료
kill %1
```

> **주의**: DB 롤백은 데이터 손실을 유발할 수 있습니다. 반드시 롤백 전 백업 상태를 확인하세요.

### 7.3 롤백 판단 기준

| 심각도 | 증상 | 대응 |
|--------|------|------|
| Critical | /health 실패, 전체 서비스 다운 | Cloud Run revision 즉시 롤백 |
| High | 5xx 에러율 > 10% | 원인 파악 후 revision 롤백 또는 핫픽스 |
| Medium | 특정 기능 오류, 성능 저하 | Staging에서 재현 후 핫픽스 배포 |
| Low | UI 이슈, 경미한 버그 | 다음 정기 배포에 수정 포함 |

---

## 8. 모니터링

### 8.1 Cloud Logging — 로그 조회

```bash
# Cloud Run 서비스 로그 실시간 조회 (tail)
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=food-ai-agent-api" \
  --limit=50 \
  --format="table(timestamp,severity,textPayload)" \
  --freshness=10m

# 에러 로그만 필터
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=food-ai-agent-api AND severity>=ERROR" \
  --limit=20 \
  --format="table(timestamp,textPayload)"

# 특정 시간 범위 조회
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=food-ai-agent-api AND timestamp>=\"2026-02-25T00:00:00Z\"" \
  --limit=100

# Cloud Console에서 로그 보기
echo "https://console.cloud.google.com/logs/query;query=resource.type%3D%22cloud_run_revision%22%20resource.labels.service_name%3D%22food-ai-agent-api%22?project=food-ai-agent-prod"
```

### 8.2 Error Reporting

```bash
# Error Reporting 활성화 (Cloud Run은 기본 활성화)
# Console에서 확인:
echo "https://console.cloud.google.com/errors?project=food-ai-agent-prod"

# gcloud CLI로 에러 그룹 확인
gcloud beta error-reporting events list --limit=10
```

### 8.3 Cloud Run 메트릭

Cloud Console에서 확인 가능한 주요 메트릭:

| 메트릭 | 설명 | 정상 범위 |
|--------|------|----------|
| Request count | 초당 요청 수 | 0~100 req/s |
| Request latency (p50/p95/p99) | 응답 시간 | p95 < 2s (일반), p95 < 30s (AI Chat) |
| Container instance count | 활성 인스턴스 수 | 1~10 |
| CPU utilization | CPU 사용률 | < 70% |
| Memory utilization | 메모리 사용률 | < 80% |
| Container startup latency | Cold start 시간 | < 5s |

```bash
# Cloud Run 서비스 상태 요약
gcloud run services describe food-ai-agent-api \
  --region=asia-northeast3 \
  --format="table(status.conditions.type,status.conditions.status,status.conditions.message)"

# Console 메트릭 페이지
echo "https://console.cloud.google.com/run/detail/asia-northeast3/food-ai-agent-api/metrics?project=food-ai-agent-prod"
```

### 8.4 업타임 체크 설정

```bash
# /health 엔드포인트 업타임 모니터링 (5분 간격)
gcloud monitoring uptime create \
  --display-name="Food AI API Health Check" \
  --uri="https://food-ai-agent-api-HASH-an.a.run.app/health" \
  --period=5m \
  --timeout=10s
```

### 8.5 예산 알림

```bash
# 월 $200 예산 알림
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="Food AI Agent Monthly Budget" \
  --budget-amount=200USD \
  --threshold-rules=percent=0.5,percent=0.9,percent=1.0
```

---

## 9. 문제 해결 (Troubleshooting)

### 9.1 SSE 스트리밍 타임아웃

**증상**: AI Chat 응답이 중간에 끊기거나 504 Gateway Timeout 발생

**원인**: Cloud Run 기본 timeout이 부족하거나 HTTP/2 설정 미비

**해결**:
```bash
# Cloud Run timeout 확인 (300s 이상이어야 함)
gcloud run services describe food-ai-agent-api \
  --region=asia-northeast3 \
  --format='value(spec.template.spec.timeoutSeconds)'

# timeout 300s로 업데이트
gcloud run services update food-ai-agent-api \
  --region=asia-northeast3 \
  --timeout=300

# HTTP/2 end-to-end 활성화 (SSE에 권장)
gcloud run services update food-ai-agent-api \
  --region=asia-northeast3 \
  --use-http2
```

**확인 포인트**:
- ReAct Agent는 최대 10 iterations 수행 가능 (각 iteration에 Claude API 호출)
- Claude API 자체 응답 시간: 3~15초/iteration
- 300초 timeout으로 충분하지만, 복잡한 쿼리는 모니터링 필요

### 9.2 VPC Connector 연결 실패

**증상**: Cloud Run에서 Cloud SQL 연결 실패 (`Connection refused`, `timeout`)

**원인**: VPC Connector 상태 이상 또는 서브넷 충돌

**해결**:
```bash
# VPC Connector 상태 확인
gcloud compute networks vpc-access connectors describe food-ai-connector \
  --region=asia-northeast3

# 정상 상태: state: READY
# 비정상 시 재생성:
gcloud compute networks vpc-access connectors delete food-ai-connector \
  --region=asia-northeast3

gcloud compute networks vpc-access connectors create food-ai-connector \
  --region=asia-northeast3 \
  --network=food-ai-vpc \
  --range=10.8.0.0/28 \
  --min-instances=2 \
  --max-instances=10

# Cloud SQL Private IP 확인
gcloud sql instances describe food-ai-db-prod \
  --format='value(ipAddresses[0].ipAddress)'
```

**확인 포인트**:
- VPC Connector 서브넷 범위 (`10.8.0.0/28`)가 다른 리소스와 충돌하지 않는지 확인
- Cloud SQL이 `--no-assign-ip` (Private IP only)로 생성되었는지 확인
- Cloud Run 서비스에 `--vpc-connector=food-ai-connector` 플래그가 설정되었는지 확인

### 9.3 pgvector 확장 없음

**증상**: Alembic 마이그레이션 중 `type "vector" does not exist` 에러

**원인**: Cloud SQL에 pgvector 확장이 활성화되지 않음

**해결**:
```bash
# Cloud SQL 인스턴스 데이터베이스 플래그 확인
gcloud sql instances describe food-ai-db-prod \
  --format='value(settings.databaseFlags)'

# cloudsql.enable_pgvector=on 플래그가 없으면 추가
gcloud sql instances patch food-ai-db-prod \
  --database-flags=cloudsql.enable_pgvector=on

# 인스턴스 재시작 필요 (자동으로 재시작됨, 약 1~2분)
# 재시작 후 psql로 접속하여 확장 활성화
psql -h 127.0.0.1 -U foodai_app -d food_ai_agent \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**확인 포인트**:
- Cloud SQL PostgreSQL 16은 pgvector 네이티브 지원 (별도 설치 불필요)
- PostgreSQL 15 이하 버전에서는 지원되지 않을 수 있음 — 버전 확인: `SELECT version();`

### 9.4 Cold Start 지연

**증상**: 첫 요청 응답이 5~10초 이상 소요

**해결**:
```bash
# Production은 min-instances=1 설정 (Cold start 방지)
gcloud run services update food-ai-agent-api \
  --region=asia-northeast3 \
  --min-instances=1

# CPU always-on (Startup 시간 단축)
gcloud run services update food-ai-agent-api \
  --region=asia-northeast3 \
  --cpu-boost
```

### 9.5 Cloud SQL 연결 수 초과

**증상**: `too many connections` 에러

**해결**:
```bash
# Cloud SQL 최대 연결 수 확인
gcloud sql instances describe food-ai-db-prod \
  --format='value(settings.tier)'
# db-custom-1-3840 → 약 200 연결 가능

# 현재 연결 수 확인 (psql)
psql -c "SELECT count(*) FROM pg_stat_activity;"

# Cloud Run 인스턴스별 pool_size 확인
# food-ai-agent-api/app/db/database.py에서 Cloud Run 환경 자동 감지:
#   pool_size=5, max_overflow=5 (인스턴스당)
# max_instances=10 → 최대 100 연결 (200 제한 내 안전)
```

### 9.6 Secret Manager 접근 실패

**증상**: Cloud Run 시작 시 `Permission denied` 또는 시크릿 값 미주입

**해결**:
```bash
# Cloud Run 서비스 계정 확인
gcloud run services describe food-ai-agent-api \
  --region=asia-northeast3 \
  --format='value(spec.template.spec.serviceAccountName)'

# 서비스 계정에 Secret Accessor 권한 부여
SA="<SERVICE_ACCOUNT_EMAIL>"
gcloud projects add-iam-policy-binding food-ai-agent-prod \
  --member="serviceAccount:$SA" \
  --role=roles/secretmanager.secretAccessor

# 시크릿 존재 여부 및 버전 확인
gcloud secrets list
gcloud secrets versions list database-url
```

### 9.7 일반 디버깅 명령어 모음

```bash
# Cloud Run 서비스 전체 상태
gcloud run services describe food-ai-agent-api --region=asia-northeast3

# 최근 배포 revision 목록
gcloud run revisions list --service=food-ai-agent-api --region=asia-northeast3 --limit=5

# Cloud SQL 인스턴스 상태
gcloud sql instances describe food-ai-db-prod

# VPC Connector 상태
gcloud compute networks vpc-access connectors describe food-ai-connector --region=asia-northeast3

# Secret Manager 시크릿 목록
gcloud secrets list

# Artifact Registry 이미지 목록
gcloud artifacts docker images list \
  asia-northeast3-docker.pkg.dev/food-ai-agent-prod/food-ai/food-ai-agent-api \
  --limit=5

# Cloud Run 로그 (최근 5분)
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=food-ai-agent-api" \
  --freshness=5m --limit=30 --format="table(timestamp,severity,textPayload)"
```

---

## Appendix: 주요 설정값 요약

| 항목 | 값 |
|------|-----|
| GCP Project | `food-ai-agent-prod` |
| Region | `asia-northeast3` (Seoul) |
| Cloud Run Service (Prod) | `food-ai-agent-api` |
| Cloud Run Service (Staging) | `food-ai-agent-api-staging` |
| Cloud SQL Instance (Prod) | `food-ai-db-prod` |
| Cloud SQL Instance (Staging) | `food-ai-db-staging` |
| Cloud SQL DB Name | `food_ai_agent` |
| Cloud SQL User | `foodai_app` |
| VPC | `food-ai-vpc` |
| VPC Connector | `food-ai-connector` (10.8.0.0/28) |
| Artifact Registry | `asia-northeast3-docker.pkg.dev/food-ai-agent-prod/food-ai` |
| Docker Image | `food-ai-agent-api` |
| CPU / Memory | 2 vCPU / 2 GiB |
| Timeout | 300s |
| Min Instances (Prod) | 1 |
| Max Instances (Prod) | 10 |
| Min Instances (Staging) | 0 |
| Max Instances (Staging) | 5 |

---

> **Contact**: 배포 관련 문의는 CTO 팀 또는 인프라 담당자에게 연락하세요.
