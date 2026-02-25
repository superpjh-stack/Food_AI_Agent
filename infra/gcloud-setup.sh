#!/usr/bin/env bash
# =============================================================================
# Food AI Agent - Google Cloud Infrastructure Provisioning Script
# =============================================================================
# One-time setup for GCloud resources:
#   Cloud Run, Cloud SQL (PG16 + pgvector), Artifact Registry,
#   Secret Manager, VPC Connector, Workload Identity Federation
#
# Usage:
#   chmod +x gcloud-setup.sh
#   ./gcloud-setup.sh
#
# Prerequisites:
#   - gcloud CLI installed and authenticated (gcloud auth login)
#   - Billing account linked to the project
#   - Owner or Editor role on the project
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration Variables
# ---------------------------------------------------------------------------
PROJECT_ID="food-ai-agent-prod"
REGION="asia-northeast3"
ZONE="${REGION}-a"

# Cloud SQL
DB_INSTANCE="food-ai-agent-db"
DB_NAME="food_ai_agent"
DB_USER="food_ai_user"
DB_TIER_DEV="db-g1-small"           # Dev/staging tier
DB_TIER_PROD="db-custom-2-7680"     # Production tier (2 vCPU, 7.5 GB)
DB_TIER="${DB_TIER_DEV}"            # Change to DB_TIER_PROD for production

# Artifact Registry
AR_REPO="food-ai"

# Cloud Run
SERVICE="food-ai-agent-api"

# VPC
VPC_CONNECTOR="food-ai-connector"
VPC_CONNECTOR_RANGE="10.8.0.0/28"
VPC_NETWORK="default"

# Service Account
SA_NAME="food-ai-api-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Workload Identity Federation (GitHub Actions)
WIF_POOL="github-pool"
WIF_PROVIDER="github-provider"
GITHUB_REPO="org/food-ai-agent"     # TODO: Replace with actual org/repo

# Secrets to create
SECRETS=("database-url" "jwt-secret" "anthropic-api-key" "openai-api-key")

# ---------------------------------------------------------------------------
# Color Helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }
section() { echo -e "\n${CYAN}============================================================${NC}"; echo -e "${CYAN}  $*${NC}"; echo -e "${CYAN}============================================================${NC}"; }

# ---------------------------------------------------------------------------
# Error handler
# ---------------------------------------------------------------------------
on_error() {
    error "Script failed at line $1. Check output above for details."
    exit 1
}
trap 'on_error $LINENO' ERR

# ---------------------------------------------------------------------------
# Pre-flight Checks
# ---------------------------------------------------------------------------
section "Pre-flight Checks"

if ! command -v gcloud &> /dev/null; then
    error "gcloud CLI is not installed. Visit https://cloud.google.com/sdk/docs/install"
    exit 1
fi
success "gcloud CLI found: $(gcloud version 2>/dev/null | head -1)"

info "Setting project to ${PROJECT_ID}..."
gcloud config set project "${PROJECT_ID}" --quiet
success "Project set to ${PROJECT_ID}"

CURRENT_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null || true)
if [ -z "${CURRENT_ACCOUNT}" ]; then
    error "No active gcloud account. Run: gcloud auth login"
    exit 1
fi
success "Authenticated as ${CURRENT_ACCOUNT}"

# ===========================================================================
# 1. Enable APIs
# ===========================================================================
section "1. Enabling Google Cloud APIs"

APIS=(
    "run.googleapis.com"                  # Cloud Run
    "sqladmin.googleapis.com"             # Cloud SQL Admin
    "secretmanager.googleapis.com"        # Secret Manager
    "artifactregistry.googleapis.com"     # Artifact Registry
    "vpcaccess.googleapis.com"            # Serverless VPC Access
    "compute.googleapis.com"              # Compute Engine (VPC)
    "iam.googleapis.com"                  # IAM
    "iamcredentials.googleapis.com"       # IAM Credentials (WIF)
    "cloudresourcemanager.googleapis.com" # Resource Manager
    "servicenetworking.googleapis.com"    # Service Networking (Private IP)
    "sts.googleapis.com"                  # Security Token Service (WIF)
)

for api in "${APIS[@]}"; do
    info "Enabling ${api}..."
    gcloud services enable "${api}" --quiet
    success "Enabled ${api}"
done

# ===========================================================================
# 2. Artifact Registry
# ===========================================================================
section "2. Creating Artifact Registry Repository"

if gcloud artifacts repositories describe "${AR_REPO}" \
    --location="${REGION}" --format="value(name)" 2>/dev/null; then
    warn "Artifact Registry repo '${AR_REPO}' already exists, skipping."
else
    gcloud artifacts repositories create "${AR_REPO}" \
        --repository-format=docker \
        --location="${REGION}" \
        --description="Food AI Agent Docker images" \
        --quiet
    success "Created Artifact Registry: ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}"
fi

# ===========================================================================
# 3. Cloud SQL (PostgreSQL 16 + pgvector)
# ===========================================================================
section "3. Creating Cloud SQL PostgreSQL 16 Instance"

warn "NOTE: For Private IP, ensure VPC peering is configured."
warn "  gcloud compute addresses create google-managed-services-default \\"
warn "    --global --purpose=VPC_PEERING --prefix-length=16 --network=default"
warn "  gcloud services vpc-peerings connect \\"
warn "    --service=servicenetworking.googleapis.com --ranges=google-managed-services-default --network=default"
echo ""

if gcloud sql instances describe "${DB_INSTANCE}" --format="value(name)" 2>/dev/null; then
    warn "Cloud SQL instance '${DB_INSTANCE}' already exists, skipping creation."
else
    info "Creating Cloud SQL instance '${DB_INSTANCE}' (tier: ${DB_TIER})..."
    info "This may take 5-10 minutes..."
    gcloud sql instances create "${DB_INSTANCE}" \
        --database-version=POSTGRES_16 \
        --tier="${DB_TIER}" \
        --region="${REGION}" \
        --storage-type=SSD \
        --storage-size=20GB \
        --storage-auto-increase \
        --backup-start-time="03:00" \
        --enable-point-in-time-recovery \
        --maintenance-window-day=SUN \
        --maintenance-window-hour=4 \
        --availability-type=zonal \
        --quiet
    success "Cloud SQL instance created: ${DB_INSTANCE}"
fi

# 3-1. Create database
info "Creating database '${DB_NAME}'..."
if gcloud sql databases describe "${DB_NAME}" --instance="${DB_INSTANCE}" 2>/dev/null; then
    warn "Database '${DB_NAME}' already exists, skipping."
else
    gcloud sql databases create "${DB_NAME}" \
        --instance="${DB_INSTANCE}" \
        --charset=UTF8 \
        --collation=en_US.UTF8 \
        --quiet
    success "Database '${DB_NAME}' created."
fi

# 3-2. Create user
info "Creating database user '${DB_USER}'..."
DB_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=')
if gcloud sql users list --instance="${DB_INSTANCE}" --format="value(name)" | grep -qx "${DB_USER}"; then
    warn "User '${DB_USER}' already exists, skipping. Password not changed."
else
    gcloud sql users create "${DB_USER}" \
        --instance="${DB_INSTANCE}" \
        --password="${DB_PASSWORD}" \
        --quiet
    success "User '${DB_USER}' created."
    warn "SAVE THIS PASSWORD (will not be shown again): ${DB_PASSWORD}"
fi

# 3-3. Enable pgvector extension
info "Enabling pgvector extension..."
warn "Run the following SQL on the database after instance is ready:"
warn "  gcloud sql connect ${DB_INSTANCE} --database=${DB_NAME} --user=postgres"
warn "  SQL> CREATE EXTENSION IF NOT EXISTS vector;"
warn "  SQL> GRANT USAGE ON SCHEMA public TO ${DB_USER};"
echo ""
success "Cloud SQL setup complete."

# ===========================================================================
# 4. VPC Connector (Serverless VPC Access)
# ===========================================================================
section "4. Creating Serverless VPC Connector"

if gcloud compute networks vpc-access connectors describe "${VPC_CONNECTOR}" \
    --region="${REGION}" --format="value(name)" 2>/dev/null; then
    warn "VPC Connector '${VPC_CONNECTOR}' already exists, skipping."
else
    info "Creating VPC connector '${VPC_CONNECTOR}' (range: ${VPC_CONNECTOR_RANGE})..."
    gcloud compute networks vpc-access connectors create "${VPC_CONNECTOR}" \
        --region="${REGION}" \
        --network="${VPC_NETWORK}" \
        --range="${VPC_CONNECTOR_RANGE}" \
        --min-instances=2 \
        --max-instances=3 \
        --machine-type=e2-micro \
        --quiet
    success "VPC Connector created: ${VPC_CONNECTOR}"
fi

# ===========================================================================
# 5. Secret Manager
# ===========================================================================
section "5. Creating Secret Manager Secrets"

for secret in "${SECRETS[@]}"; do
    if gcloud secrets describe "${secret}" --format="value(name)" 2>/dev/null; then
        warn "Secret '${secret}' already exists, skipping."
    else
        echo -n "PLACEHOLDER_REPLACE_ME" | gcloud secrets create "${secret}" \
            --data-file=- \
            --replication-policy="user-managed" \
            --locations="${REGION}" \
            --quiet
        success "Secret '${secret}' created (placeholder value, update before deploy)."
    fi
done

warn "Update secrets with real values before deploying:"
warn "  echo -n 'real-value' | gcloud secrets versions add database-url --data-file=-"
warn "  echo -n 'real-value' | gcloud secrets versions add jwt-secret --data-file=-"
warn "  echo -n 'real-value' | gcloud secrets versions add anthropic-api-key --data-file=-"
warn "  echo -n 'real-value' | gcloud secrets versions add openai-api-key --data-file=-"

# ===========================================================================
# 6. Service Accounts
# ===========================================================================
section "6. Creating Service Accounts & IAM Bindings"

# 6-1. Cloud Run Service Account
if gcloud iam service-accounts describe "${SA_EMAIL}" 2>/dev/null; then
    warn "Service account '${SA_EMAIL}' already exists, skipping creation."
else
    gcloud iam service-accounts create "${SA_NAME}" \
        --display-name="Food AI Agent API (Cloud Run)" \
        --description="Service account for Food AI Agent Cloud Run service" \
        --quiet
    success "Service account created: ${SA_EMAIL}"
fi

# 6-2. Grant IAM Roles
IAM_ROLES=(
    "roles/cloudsql.client"           # Cloud SQL Client
    "roles/secretmanager.secretAccessor" # Secret Manager Accessor
    "roles/storage.objectViewer"      # Cloud Storage Object Viewer
    "roles/run.invoker"               # Allow Cloud Run invocation (for IAP/auth)
)

for role in "${IAM_ROLES[@]}"; do
    info "Granting ${role} to ${SA_EMAIL}..."
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="${role}" \
        --condition=None \
        --quiet > /dev/null 2>&1
    success "Granted ${role}"
done

# ===========================================================================
# 7. Workload Identity Federation (GitHub Actions OIDC)
# ===========================================================================
section "7. Setting Up Workload Identity Federation"

# 7-1. Create WIF Pool
if gcloud iam workload-identity-pools describe "${WIF_POOL}" \
    --location="global" --format="value(name)" 2>/dev/null; then
    warn "WIF pool '${WIF_POOL}' already exists, skipping."
else
    gcloud iam workload-identity-pools create "${WIF_POOL}" \
        --location="global" \
        --display-name="GitHub Actions Pool" \
        --description="WIF pool for GitHub Actions CI/CD" \
        --quiet
    success "WIF pool created: ${WIF_POOL}"
fi

# 7-2. Create WIF Provider
WIF_POOL_ID=$(gcloud iam workload-identity-pools describe "${WIF_POOL}" \
    --location="global" --format="value(name)" 2>/dev/null || true)

if gcloud iam workload-identity-pools providers describe "${WIF_PROVIDER}" \
    --workload-identity-pool="${WIF_POOL}" \
    --location="global" --format="value(name)" 2>/dev/null; then
    warn "WIF provider '${WIF_PROVIDER}' already exists, skipping."
else
    gcloud iam workload-identity-pools providers create-oidc "${WIF_PROVIDER}" \
        --location="global" \
        --workload-identity-pool="${WIF_POOL}" \
        --display-name="GitHub Provider" \
        --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
        --issuer-uri="https://token.actions.githubusercontent.com" \
        --attribute-condition="assertion.repository=='${GITHUB_REPO}'" \
        --quiet
    success "WIF provider created: ${WIF_PROVIDER}"
fi

# 7-3. Bind SA to WIF (allow GitHub Actions to impersonate)
WIF_PROVIDER_FULL=$(gcloud iam workload-identity-pools providers describe "${WIF_PROVIDER}" \
    --workload-identity-pool="${WIF_POOL}" \
    --location="global" \
    --format="value(name)" 2>/dev/null || true)

if [ -n "${WIF_PROVIDER_FULL}" ]; then
    # Grant the SA the ability to be impersonated by GitHub Actions
    gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
        --role="roles/iam.workloadIdentityUser" \
        --member="principalSet://iam.googleapis.com/${WIF_POOL_ID}/attribute.repository/${GITHUB_REPO}" \
        --quiet > /dev/null 2>&1
    success "WIF binding complete: GitHub repo '${GITHUB_REPO}' can impersonate ${SA_EMAIL}"

    # Grant deploy permissions to the SA
    DEPLOY_ROLES=(
        "roles/run.admin"                  # Deploy to Cloud Run
        "roles/artifactregistry.writer"    # Push Docker images
        "roles/iam.serviceAccountUser"     # Act as SA for Cloud Run
    )
    for role in "${DEPLOY_ROLES[@]}"; do
        gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
            --member="serviceAccount:${SA_EMAIL}" \
            --role="${role}" \
            --condition=None \
            --quiet > /dev/null 2>&1
        success "Granted deploy role: ${role}"
    done
else
    warn "Could not retrieve WIF provider full name. Verify WIF setup manually."
fi

# ===========================================================================
# 8. Initial Cloud Run Deployment (Placeholder)
# ===========================================================================
section "8. Creating Cloud Run Service (Placeholder)"

info "Deploying placeholder Cloud Run service '${SERVICE}'..."
gcloud run deploy "${SERVICE}" \
    --image="gcr.io/cloudrun/placeholder" \
    --region="${REGION}" \
    --platform=managed \
    --service-account="${SA_EMAIL}" \
    --vpc-connector="${VPC_CONNECTOR}" \
    --set-secrets="DATABASE_URL=database-url:latest,JWT_SECRET_KEY=jwt-secret:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest,OPENAI_API_KEY=openai-api-key:latest" \
    --set-env-vars="APP_ENV=production,DEBUG=false,CLAUDE_MODEL=claude-sonnet-4-6" \
    --timeout=300 \
    --cpu=2 \
    --memory=2Gi \
    --min-instances=0 \
    --max-instances=10 \
    --port=8000 \
    --allow-unauthenticated \
    --quiet
success "Cloud Run service '${SERVICE}' created (placeholder image)."

# ===========================================================================
# 9. Summary
# ===========================================================================
section "SETUP COMPLETE - Resource Summary"

# Fetch Cloud SQL connection name
SQL_CONNECTION=$(gcloud sql instances describe "${DB_INSTANCE}" \
    --format="value(connectionName)" 2>/dev/null || echo "N/A")

# Fetch WIF provider full resource name
WIF_PROVIDER_RESOURCE=$(gcloud iam workload-identity-pools providers describe "${WIF_PROVIDER}" \
    --workload-identity-pool="${WIF_POOL}" \
    --location="global" \
    --format="value(name)" 2>/dev/null || echo "N/A")

# Fetch Cloud Run URL
SERVICE_URL=$(gcloud run services describe "${SERVICE}" \
    --region="${REGION}" \
    --format="value(status.url)" 2>/dev/null || echo "N/A")

echo ""
echo -e "${GREEN}Project${NC}:              ${PROJECT_ID}"
echo -e "${GREEN}Region${NC}:               ${REGION}"
echo ""
echo -e "${CYAN}--- Artifact Registry ---${NC}"
echo -e "  Repository:          ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}"
echo ""
echo -e "${CYAN}--- Cloud SQL ---${NC}"
echo -e "  Instance:            ${DB_INSTANCE}"
echo -e "  Connection Name:     ${SQL_CONNECTION}"
echo -e "  Database:            ${DB_NAME}"
echo -e "  User:                ${DB_USER}"
echo -e "  Tier:                ${DB_TIER}"
echo ""
echo -e "${CYAN}--- VPC Connector ---${NC}"
echo -e "  Name:                ${VPC_CONNECTOR}"
echo -e "  IP Range:            ${VPC_CONNECTOR_RANGE}"
echo ""
echo -e "${CYAN}--- Secret Manager ---${NC}"
for secret in "${SECRETS[@]}"; do
    echo -e "  Secret:              ${secret}"
done
echo ""
echo -e "${CYAN}--- Service Account ---${NC}"
echo -e "  Email:               ${SA_EMAIL}"
echo ""
echo -e "${CYAN}--- Workload Identity Federation ---${NC}"
echo -e "  Pool:                ${WIF_POOL}"
echo -e "  Provider:            ${WIF_PROVIDER}"
echo -e "  Provider Resource:   ${WIF_PROVIDER_RESOURCE}"
echo -e "  GitHub Repo:         ${GITHUB_REPO}"
echo ""
echo -e "${CYAN}--- Cloud Run ---${NC}"
echo -e "  Service:             ${SERVICE}"
echo -e "  URL:                 ${SERVICE_URL}"
echo ""
echo -e "${YELLOW}--- Next Steps ---${NC}"
echo "  1. Update GITHUB_REPO variable in this script to actual repo"
echo "  2. Set up VPC peering for Cloud SQL Private IP (see warnings above)"
echo "  3. Connect to Cloud SQL and enable pgvector:"
echo "     gcloud sql connect ${DB_INSTANCE} --database=${DB_NAME} --user=postgres"
echo "     SQL> CREATE EXTENSION IF NOT EXISTS vector;"
echo "  4. Update Secret Manager values with real credentials:"
echo "     echo -n 'postgresql+asyncpg://${DB_USER}:PASS@/food_ai_agent?host=/cloudsql/${SQL_CONNECTION}' \\"
echo "       | gcloud secrets versions add database-url --data-file=-"
echo "  5. Set up GitHub Repository Secrets (see infra/github-secrets-setup.md)"
echo "  6. Build & push Docker image, then redeploy Cloud Run"
echo "  7. Run Alembic migrations against Cloud SQL"
echo ""
success "Infrastructure provisioning complete!"
