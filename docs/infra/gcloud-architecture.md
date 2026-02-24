# Google Cloud 배포 아키텍처

> Food AI Agent — GCloud 마이그레이션 (Supabase/Railway → Google Cloud)
> 작성일: 2026-02-24 | CTO Team Review

## 서비스 매핑

| 구분 | 이전 (Supabase/Railway) | 현재 (Google Cloud) |
|------|------------------------|---------------------|
| API 서버 | Railway / Fly.io | **Cloud Run Gen2** (asia-northeast3) |
| 데이터베이스 | Supabase / Railway PG | **Cloud SQL PostgreSQL 16** (Private IP) |
| pgvector | Supabase 내장 | Cloud SQL 네이티브 지원 (`CREATE EXTENSION vector`) |
| 파일 스토리지 | 로컬 / MinIO | **Cloud Storage** (GCS, S3 호환) |
| 환경 변수/시크릿 | Railway 환경변수 | **Secret Manager** |
| Docker 레지스트리 | Docker Hub | **Artifact Registry** |
| Frontend | Vercel | **Vercel** (유지, Next.js 최적화) |
| CI/CD | 없음 | **GitHub Actions + WIF** |

## 아키텍처 다이어그램

```
                        인터넷
                          │
              ┌───────────┴───────────┐
              │                       │
         Vercel CDN              Cloud Run
         (Next.js FE)          (FastAPI API)
         글로벌 엣지             asia-northeast3
              │                       │
              │                  VPC Connector
              │                 (food-ai-connector)
              │                  10.8.0.0/28
              │                       │
              └───────────┬───────────┘
                          │
                   VPC: food-ai-vpc
                   (10.0.0.0/16)
                          │
           ┌──────────────┼──────────────┐
           │              │              │
    Cloud SQL          Cloud Storage  Secret Manager
    PG16+pgvector      (문서/사진)    (API Keys, JWT)
    Private IP Only
    10.0.1.x
```

## Cloud Run 설정

| 항목 | 값 | 이유 |
|------|-----|------|
| Region | asia-northeast3 (서울) | 사용자(한국) 레이턴시 최소화 |
| CPU | 2 vCPU | RAG 추론 + Claude 스트리밍 |
| Memory | 2 GiB | pgvector 임베딩 캐시 |
| Min Instances | 1 (production) | Cold start 제거 |
| Max Instances | 10 | 피크 트래픽 대응 |
| Timeout | 300s | ReAct Agent 멀티스텝 (최대 10 iterations) |
| Concurrency | 80 | SSE 스트리밍 + async FastAPI |

**SSE 스트리밍 주의사항**: Cloud Run Gen2는 HTTP/2 + 긴 연결 지원. `timeoutSeconds: 300` 으로 AI 에이전트 루프 완료 보장.

## Cloud SQL 설정

| 항목 | 값 |
|------|-----|
| 엔진 | PostgreSQL 16 |
| Tier | db-custom-1-3840 (1 vCPU, 3.75GB) |
| Storage | SSD 50GB (자동 확장) |
| Connection | Private IP Only (공용 IP 없음) |
| pgvector | 네이티브 지원, 별도 설정 불필요 |
| Backup | 자동 일별 백업, 7일 보관 |
| HA | 단일 존 (초기), 리전 복제본 (확장 시) |

**pgvector 활성화 (Cloud SQL)**:
```sql
-- Cloud SQL에서 pgvector 활성화 (기존 Alembic 마이그레이션과 동일)
CREATE EXTENSION IF NOT EXISTS vector;
-- 기존 migrations/001_initial_schema.py 코드 그대로 동작
```

## DB 연결 URL 형식

```bash
# Cloud Run → Cloud SQL (Unix Socket, 권장)
DATABASE_URL=postgresql+asyncpg://user:pass@/food_ai_agent?host=/cloudsql/PROJECT:asia-northeast3:INSTANCE

# VPC Private IP (대안)
DATABASE_URL=postgresql+asyncpg://user:pass@10.x.x.x:5432/food_ai_agent
```

## Connection Pool 조정 (`app/db/database.py`)

Cloud SQL 연결 수 제한 대응:
```python
# Cloud Run 환경 감지 (K_SERVICE 환경변수로 자동 판별)
_is_cloud_run = os.getenv("K_SERVICE") is not None
pool_size     = 5  if _is_cloud_run else 20
max_overflow  = 5  if _is_cloud_run else 10
```

Cloud SQL 티어별 최대 연결 수:
- `db-f1-micro`: ~25개 (개발/스테이징)
- `db-custom-1-3840`: ~200개 (production)

## Secret Manager 시크릿 목록

| 시크릿 이름 | 값 |
|-------------|-----|
| `database-url` | Cloud SQL 연결 URL |
| `jwt-secret` | JWT 서명 키 |
| `anthropic-api-key` | Claude API 키 |
| `openai-api-key` | OpenAI 임베딩 키 |

```bash
# Secret 생성 명령어
echo -n "postgresql+asyncpg://..." | gcloud secrets create database-url --data-file=-
echo -n "your-jwt-secret" | gcloud secrets create jwt-secret --data-file=-
echo -n "sk-ant-..." | gcloud secrets create anthropic-api-key --data-file=-
echo -n "sk-..." | gcloud secrets create openai-api-key --data-file=-
```

## CI/CD 파이프라인

```
feature/* push
  └─→ CI (pytest 52개 + pgvector/pgvector:pg16)
         │
main merge
  └─→ Build → Artifact Registry
         └─→ Deploy Staging (자동)
               └─→ Smoke Test (/health)
                     └─→ [수동 승인]
                           └─→ Deploy Production (canary 옵션)
```

**GitHub Secrets 필요 항목**:
| Secret | 용도 |
|--------|------|
| `WIF_PROVIDER` | Workload Identity Provider |
| `WIF_SA_EMAIL` | Service Account Email |
| `ANTHROPIC_API_KEY_TEST` | CI 테스트용 (minimal) |
| `OPENAI_API_KEY_TEST` | CI 테스트용 임베딩 |

**Workload Identity Federation 설정** (서비스 계정 키 없이 GitHub Actions 인증):
```bash
gcloud iam workload-identity-pools create github-pool \
  --location=global --display-name="GitHub Actions Pool"

gcloud iam workload-identity-pools providers create-oidc github-provider \
  --workload-identity-pool=github-pool \
  --issuer-uri=https://token.actions.githubusercontent.com \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --location=global
```

## 비용 추정 (월간, 10K req/day 기준)

| 서비스 | 예상 비용 |
|--------|----------|
| Cloud Run | $15-30 |
| Cloud SQL (db-custom-1-3840) | ~$50 |
| Artifact Registry | ~$2 |
| Secret Manager | ~$0.5 |
| Cloud Storage | ~$2 |
| VPC Connector | ~$7 |
| Cloud Monitoring | ~$0-5 |
| **합계** | **$76-97/월** |

*비교: Supabase Pro + Railway ~$45-65/월*

## 마이그레이션 절차 (5~6일)

### Day 1-2: GCP 인프라 구축
```bash
# 1. GCP 프로젝트 + API 활성화
gcloud projects create food-ai-agent-prod
gcloud services enable run.googleapis.com sqladmin.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com \
  vpcaccess.googleapis.com

# 2. VPC + Serverless VPC Connector
gcloud compute networks create food-ai-vpc --subnet-mode=auto
gcloud compute networks vpc-access connectors create food-ai-connector \
  --region=asia-northeast3 --network=food-ai-vpc --range=10.8.0.0/28

# 3. Cloud SQL
gcloud sql instances create food-ai-agent-db \
  --database-version=POSTGRES_16 \
  --tier=db-custom-1-3840 \
  --region=asia-northeast3 \
  --no-assign-ip \
  --network=food-ai-vpc \
  --database-flags=cloudsql.enable_pgvector=on

gcloud sql databases create food_ai_agent --instance=food-ai-agent-db

# 4. Artifact Registry
gcloud artifacts repositories create food-ai \
  --repository-format=docker --location=asia-northeast3
```

### Day 2-3: 데이터베이스 이전
```bash
# Supabase/Railway에서 덤프
pg_dump --format=custom --no-owner food_ai_agent > backup.dump

# Cloud Storage 경유 Cloud SQL import
gsutil cp backup.dump gs://food-ai-backups/
gcloud sql import pg food-ai-agent-db gs://food-ai-backups/backup.dump \
  --database=food_ai_agent

# pgvector 확인
gcloud sql connect food-ai-agent-db --user=postgres
# SELECT * FROM pg_extension WHERE extname = 'vector';
```

### Day 3-4: Cloud Run 배포
```bash
# Docker 빌드 + 푸시
docker build -t asia-northeast3-docker.pkg.dev/PROJECT/food-ai/api:v1 food-ai-agent-api/
docker push asia-northeast3-docker.pkg.dev/PROJECT/food-ai/api:v1

# Staging 배포
gcloud run deploy food-ai-agent-api-staging \
  --image=asia-northeast3-docker.pkg.dev/PROJECT/food-ai/api:v1 \
  --region=asia-northeast3 --allow-unauthenticated \
  --add-cloudsql-instances=PROJECT:asia-northeast3:food-ai-agent-db \
  --vpc-connector=food-ai-connector \
  --set-secrets="DATABASE_URL=database-url:latest,JWT_SECRET_KEY=jwt-secret:latest" \
  --set-env-vars="APP_ENV=staging,CLAUDE_MODEL=claude-sonnet-4-6" \
  --timeout=300 --cpu=2 --memory=2Gi --min-instances=0 --max-instances=5
```

### Day 4-5: CI/CD + 모니터링
- `.github/workflows/deploy-api.yml` 활성화 (이미 생성됨)
- Cloud Monitoring: `/health` 업타임 체크, 에러율 5% 초과 알림
- Budget Alert: $100, $200 초과 시 이메일 알림

### Day 5-6: 프로덕션 전환 + 구 서비스 종료
- DNS 전환 (api.foodai.example.com → Cloud Run URL)
- Vercel 환경변수 `NEXT_PUBLIC_API_URL` 업데이트
- 1주일 후 Supabase/Railway 종료

## 위험 요소 및 대책

| 위험 | 심각도 | 대책 |
|------|--------|------|
| Cloud SQL 연결 수 초과 | 높음 | pool_size=5 (Cloud Run 환경 자동 감지) |
| pgvector 성능 차이 | 중간 | Staging에서 벡터 검색 벤치마크 선 수행 |
| SSE Cold Start 지연 | 중간 | min-instances=1 (production) |
| 비용 초과 | 낮음 | Budget Alert $200 설정 |
| 데이터 유실 | 매우 낮음 | pg_dump + Cloud SQL 자동 백업 중첩 |
