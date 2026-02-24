# GCloud Deploy Plan: Google Cloud 실배포

- **문서 버전**: 1.0.0
- **작성일**: 2026-02-24
- **PDCA 단계**: Plan
- **참조 아키텍처**: `docs/infra/gcloud-architecture.md`

---

## 1. 개요

### 1.1 목적

MVP 1+2+3이 완성된 Food AI Agent를 **Google Cloud Platform**에 실 운영 환경으로 배포한다.
현재 로컬 개발 환경 → Staging → Production 파이프라인을 구축하여 파일럿 고객 운영을 시작한다.

### 1.2 배포 대상 환경

| 환경 | 용도 | 도메인 (예시) |
|------|------|--------------|
| Staging | QA / 내부 검증 | `staging-api.foodai.kr` |
| Production | 실 운영 / 파일럿 고객 | `api.foodai.kr` |
| Frontend (Vercel) | 글로벌 CDN | `app.foodai.kr` |

### 1.3 현재 상태 (기구현 완료)

- ✅ `food-ai-agent-api/Dockerfile` — API 컨테이너
- ✅ `food-ai-agent-web/Dockerfile` — Frontend 컨테이너
- ✅ `.github/workflows/deploy-api.yml` — CI/CD 워크플로우
- ✅ `docker-compose.prod.yml` — 로컬 프로덕션 테스트
- ✅ `docs/infra/gcloud-architecture.md` — 아키텍처 상세
- ✅ `food-ai-agent-api/app/db/database.py` — Cloud Run pool_size 자동 감지

### 1.4 필요 작업 (이번 Plan 범위)

| 카테고리 | 항목 |
|----------|------|
| GCP 인프라 | 프로젝트, VPC, Cloud SQL, Artifact Registry, Secret Manager |
| 컨테이너 | Dockerfile multi-stage 최적화, 프로덕션 이미지 빌드 |
| CI/CD | GitHub Actions WIF 설정, Secrets 등록, Environments 구성 |
| DB 마이그레이션 | 스키마 초기화 (Alembic) + 시드 데이터 |
| Frontend | Vercel 프로젝트 연동, 환경변수 설정 |
| 모니터링 | Cloud Monitoring 업타임 체크, 알림 정책 |
| 보안 | Cloud Armor WAF, HTTPS 인증서, CORS 설정 |

---

## 2. GCP 인프라 프로비저닝

### 2.1 프로젝트 및 API 활성화

```bash
# GCP 프로젝트 생성
gcloud projects create food-ai-agent-prod --name="Food AI Agent"
gcloud config set project food-ai-agent-prod

# 필수 API 활성화
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  vpcaccess.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iam.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com
```

### 2.2 VPC + Serverless VPC Access Connector

```bash
# VPC 생성 (Private Services Access 포함)
gcloud compute networks create food-ai-vpc \
  --subnet-mode=auto --bgp-routing-mode=regional

# Private Services Access (Cloud SQL private IP용)
gcloud compute addresses create google-managed-services-food-ai-vpc \
  --global --purpose=VPC_PEERING --prefix-length=16 \
  --network=food-ai-vpc
gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=google-managed-services-food-ai-vpc \
  --network=food-ai-vpc

# Serverless VPC Connector (Cloud Run → Cloud SQL)
gcloud compute networks vpc-access connectors create food-ai-connector \
  --region=asia-northeast3 \
  --network=food-ai-vpc \
  --range=10.8.0.0/28 \
  --min-instances=2 \
  --max-instances=10
```

### 2.3 Cloud SQL (PostgreSQL 16 + pgvector)

```bash
# Cloud SQL 인스턴스 생성 (Staging: f1-micro, Production: custom-1-3840)
# --- Staging ---
gcloud sql instances create food-ai-db-staging \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=asia-northeast3 \
  --no-assign-ip \
  --network=food-ai-vpc \
  --database-flags=cloudsql.enable_pgvector=on \
  --backup-start-time=03:00 \
  --availability-type=zonal

# --- Production ---
gcloud sql instances create food-ai-db-prod \
  --database-version=POSTGRES_16 \
  --tier=db-custom-1-3840 \
  --region=asia-northeast3 \
  --no-assign-ip \
  --network=food-ai-vpc \
  --database-flags=cloudsql.enable_pgvector=on \
  --backup-start-time=02:00 \
  --backup-retention=7 \
  --availability-type=zonal

# DB + User 생성
gcloud sql databases create food_ai_agent --instance=food-ai-db-prod
gcloud sql users create foodai_app \
  --instance=food-ai-db-prod \
  --password=<STRONG_PASSWORD>
```

### 2.4 Artifact Registry

```bash
gcloud artifacts repositories create food-ai \
  --repository-format=docker \
  --location=asia-northeast3 \
  --description="Food AI Agent Docker images"
```

### 2.5 Secret Manager

```bash
# DATABASE_URL (Cloud SQL Unix socket 형식)
echo -n "postgresql+asyncpg://foodai_app:<PW>@/food_ai_agent?host=/cloudsql/food-ai-agent-prod:asia-northeast3:food-ai-db-prod" \
  | gcloud secrets create database-url --data-file=-

# JWT
openssl rand -base64 64 | tr -d '\n' \
  | gcloud secrets create jwt-secret --data-file=-

# API Keys
echo -n "sk-ant-YOUR_KEY" | gcloud secrets create anthropic-api-key --data-file=-
echo -n "sk-YOUR_KEY"     | gcloud secrets create openai-api-key --data-file=-

# Staging용 별도 시크릿 (동일 형식, staging DB URL)
echo -n "postgresql+asyncpg://..." | gcloud secrets create database-url-staging --data-file=-
```

---

## 3. Dockerfile 최적화 (multi-stage)

### 3.1 API Dockerfile 개선

현재 `food-ai-agent-api/Dockerfile`은 단일 스테이지. Production용 multi-stage 빌드로 최적화:

```dockerfile
# Stage 1: builder (빌드 도구 포함)
FROM python:3.11-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: production (최소 이미지)
FROM python:3.11-slim AS production
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

### 3.2 .dockerignore 추가

```
.env
.env.*
__pycache__
*.pyc
.pytest_cache
tests/
*.md
.git
alembic/versions/
```

---

## 4. DB 마이그레이션 전략

### 4.1 초기 배포 (스키마 없는 새 DB)

```bash
# Cloud SQL Auth Proxy로 로컬에서 마이그레이션 실행
./cloud-sql-proxy food-ai-agent-prod:asia-northeast3:food-ai-db-prod &

DATABASE_URL="postgresql+asyncpg://foodai_app:<PW>@localhost:5432/food_ai_agent" \
  alembic upgrade head

# 시드 데이터 (초기 마스터 데이터)
DATABASE_URL="..." python -m app.seed
```

### 4.2 Cloud Run 배포 시 자동 마이그레이션

Cloud Run 컨테이너 시작 시 마이그레이션 자동 실행 옵션:

```dockerfile
# Dockerfile CMD → startup.sh로 교체
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

> **주의**: Cloud Run은 여러 인스턴스가 동시 시작 가능 → `alembic upgrade head`의 멱등성(idempotent) 확인 필요

---

## 5. GitHub Actions CI/CD 설정

### 5.1 Workload Identity Federation (WIF) 설정

```bash
# WIF Pool 생성
gcloud iam workload-identity-pools create github-pool \
  --location=global \
  --display-name="GitHub Actions Pool"

# WIF Provider 생성
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --workload-identity-pool=github-pool \
  --location=global \
  --issuer-uri=https://token.actions.githubusercontent.com \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository"

# Service Account 생성
gcloud iam service-accounts create github-actions-sa \
  --display-name="GitHub Actions Service Account"

# 권한 부여
REPO="your-org/food-ai-agent"
SA="github-actions-sa@food-ai-agent-prod.iam.gserviceaccount.com"
POOL="projects/food-ai-agent-prod/locations/global/workloadIdentityPools/github-pool"

gcloud iam service-accounts add-iam-policy-binding $SA \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/${POOL}/attribute.repository/${REPO}"

# 필요 권한
gcloud projects add-iam-policy-binding food-ai-agent-prod \
  --member="serviceAccount:$SA" \
  --role=roles/run.admin
gcloud projects add-iam-policy-binding food-ai-agent-prod \
  --member="serviceAccount:$SA" \
  --role=roles/artifactregistry.writer
gcloud projects add-iam-policy-binding food-ai-agent-prod \
  --member="serviceAccount:$SA" \
  --role=roles/secretmanager.secretAccessor
gcloud projects add-iam-policy-binding food-ai-agent-prod \
  --member="serviceAccount:$SA" \
  --role=roles/iam.serviceAccountUser
```

### 5.2 GitHub Secrets/Variables 등록

```
# GitHub Repository Secrets (Settings → Secrets and variables → Actions)
WIF_PROVIDER         = projects/.../locations/global/workloadIdentityPools/github-pool/providers/github-provider
WIF_SA_EMAIL         = github-actions-sa@food-ai-agent-prod.iam.gserviceaccount.com
CLOUD_SQL_INSTANCE   = food-ai-agent-prod:asia-northeast3:food-ai-db-prod
ANTHROPIC_API_KEY_TEST = sk-ant-... (테스트용, 별도 키 권장)
OPENAI_API_KEY_TEST    = sk-...
```

### 5.3 GitHub Environments 설정

```
staging:    자동 배포 (main merge 시)
production: 수동 승인 (Required reviewer 지정)
```

---

## 6. Frontend (Vercel) 배포

### 6.1 Vercel 프로젝트 연동

```bash
# Vercel CLI 또는 대시보드에서
vercel link   # GitHub repo 연결
vercel env add NEXT_PUBLIC_API_URL  # 환경변수 설정
```

### 6.2 환경변수 설정

| 환경 | 변수 | 값 |
|------|------|----|
| Preview | `NEXT_PUBLIC_API_URL` | `https://food-ai-agent-api-staging-xxxx-an.a.run.app/api/v1` |
| Production | `NEXT_PUBLIC_API_URL` | `https://api.foodai.kr/api/v1` |

### 6.3 커스텀 도메인 설정

```
Vercel Dashboard → Settings → Domains
app.foodai.kr → CNAME → cname.vercel-dns.com
```

---

## 7. 모니터링 및 알림

### 7.1 Cloud Monitoring 업타임 체크

```bash
# /health 엔드포인트 업타임 체크 (5분 간격)
gcloud monitoring uptime create \
  --display-name="Food AI API Health" \
  --uri="https://api.foodai.kr/health" \
  --period=5m
```

### 7.2 알림 정책

| 알림 | 조건 | 채널 |
|------|------|------|
| API 다운 | /health 응답 없음 2분 이상 | 이메일 + Slack |
| 에러율 급등 | 5xx 에러율 > 5% (5분) | 이메일 |
| Cloud SQL CPU | > 80% (10분) | 이메일 |
| 비용 초과 | $100, $200 월 누적 | 이메일 |

### 7.3 Cloud Logging 로그 수집

FastAPI 구조화 로그 → Cloud Logging 자동 수집 (Cloud Run 기본)

---

## 8. 보안 설정

### 8.1 CORS 프로덕션 설정

```bash
# Cloud Run 환경변수
CORS_ORIGINS='["https://app.foodai.kr"]'
```

### 8.2 Cloud Armor (선택, 추후 추가)

```bash
# 기본 WAF 정책 (OWASP Top 10 방어)
gcloud compute security-policies create food-ai-waf \
  --description="WAF for Food AI Agent API"
```

---

## 9. 개발 일정 (5~6일)

| 일차 | 작업 |
|------|------|
| Day 1 | GCP 프로젝트 + API 활성화 + VPC + Cloud SQL (Staging) |
| Day 2 | Artifact Registry + Secret Manager + Dockerfile 최적화 |
| Day 3 | GitHub Actions WIF 설정 + Secrets 등록 + Staging 첫 배포 |
| Day 4 | DB 마이그레이션 + 시드 데이터 + Staging E2E 테스트 |
| Day 5 | Vercel 연동 + 커스텀 도메인 + Production 배포 |
| Day 6 | 모니터링 설정 + 알림 정책 + 부하 테스트 + 문서화 |

---

## 10. 완료 기준 (Done Criteria)

- [ ] Staging API: `https://staging-api.foodai.kr/health` 200 OK
- [ ] Production API: `https://api.foodai.kr/health` 200 OK
- [ ] Frontend: `https://app.foodai.kr` 로그인 화면 정상 표시
- [ ] AI Chat: SSE 스트리밍 응답 정상 (Claude API 연결)
- [ ] DB: Alembic 마이그레이션 완료 (003 버전 반영)
- [ ] pgvector: `SELECT * FROM pg_extension WHERE extname = 'vector'` 확인
- [ ] CI/CD: `main` 브랜치 push → Staging 자동 배포 (5분 이내)
- [ ] Monitoring: /health 업타임 체크 활성화
- [ ] Budget Alert: $200 초과 시 이메일 알림 설정

---

## 11. 롤백 계획

| 상황 | 롤백 방법 |
|------|----------|
| Cloud Run 배포 실패 | `gcloud run services update-traffic` → 이전 revision 100% |
| DB 마이그레이션 실패 | `alembic downgrade -1` |
| 심각한 버그 발견 | Cloud Run traffic split → 이전 이미지 tag로 재배포 |

```bash
# 즉시 롤백 명령어
gcloud run services update-traffic food-ai-agent-api \
  --to-revisions=PREV_REVISION=100 \
  --region=asia-northeast3
```

---

## 12. 비용 모니터링

```bash
# 월 예산 알림 설정
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="Food AI Agent Budget" \
  --budget-amount=200USD \
  --threshold-rules=percent=0.5,percent=0.9,percent=1.0
```

예상 월 비용: $76~97 (10K req/day 기준, `docs/infra/gcloud-architecture.md` §5 참고)
