---
date: 2026-04-14
topic: aws-terraform-deployment
---

# AWS Deployment with Terraform — Free Tier

## What We're Building

Terraform-managed AWS infrastructure to deploy genalphacli on AWS free tier using 2 EC2 instances + RDS + Vercel.

## Architecture

```
                    ┌─────────────────┐
                    │   Vercel (free)  │
                    │   Next.js        │
                    │   Frontend       │
                    └────────┬────────┘
                             │ /api/* proxy
                             ▼
┌──────────────────────────────────────────────────┐
│  AWS VPC                                          │
│                                                   │
│  EC2 #1 "Backend" (t2.micro, 1GB)                │
│  ├── Docker Compose                               │
│  │   ├── Core API (:8000)        ~100MB          │
│  │   ├── TPS API (:8001)         ~100MB          │
│  │   └── Worker                  ~150MB          │
│  └── Nginx (reverse proxy)       ~50MB           │
│       Total: ~400MB ✓                            │
│                                                   │
│  EC2 #2 "Infra" (t2.micro, 1GB)                  │
│  ├── Docker Compose                               │
│  │   ├── Temporal Server         ~400MB          │
│  │   ├── Temporal UI (:8080)     ~100MB          │
│  │   └── PostgreSQL (Temporal)   ~200MB          │
│  └── Total: ~700MB (tight, add 1GB swap)         │
│                                                   │
│  RDS db.t3.micro (free tier)                      │
│  └── PostgreSQL 16                                │
│      ├── core database                            │
│      └── tps database                             │
│                                                   │
│  Elastic IPs (static — survive restarts)           │
│  ├── eip-backend → EC2 #1                         │
│  └── eip-infra → EC2 #2                           │
│                                                   │
│  Security Groups                                  │
│  ├── sg-backend: 80, 443 from anywhere; 22 from my IP │
│  ├── sg-infra: 7233 from sg-backend; 8080, 22 from my IP │
│  └── sg-rds: 5432 from sg-backend + sg-infra     │
└──────────────────────────────────────────────────┘
```

## Key Decisions

### 1. Infrastructure Split
- **EC2 #1 (Backend):** Core + TPS + Worker — the application services
- **EC2 #2 (Infra):** Temporal + its PostgreSQL — the workflow engine
- **RDS:** App databases (core + tps) — managed, free tier, automated backups
- **Vercel:** Frontend — free, CDN, automatic deploys from GitHub

### 2. Why Self-Host Temporal (not Cloud)
- Unlimited workflow actions (Cloud free tier = 1000/mo)
- Full control over Temporal version and config
- ~700MB RAM on t2.micro with swap is manageable

### 3. Vercel → EC2 Connectivity
- Elastic IPs on both EC2 instances (static, survive restarts)
- Vercel frontend proxies `/api/*` to `http://<elastic-ip>:80`
- Initially HTTP-only (Vercel allows HTTP proxy targets in development)
- Add domain + Let's Encrypt SSL later for production HTTPS

### 4. Domain & SSL
- No domain yet — use EC2 Elastic IPs initially
- Nginx on EC2 #1 as reverse proxy
- Add Let's Encrypt SSL when domain is ready

### 4. CI/CD
- GitHub Actions: push to main → build Docker images → SSH deploy to EC2
- Docker images built in CI, pushed to EC2 via SSH + docker compose

### 5. Vercel Frontend
- Managed via Terraform Vercel provider
- Auto-deploys from GitHub on push to main
- Environment variables (CORE_API_URL) set via Terraform

### 6. Terraform Resources

```
# AWS
aws_vpc + subnets (public)
aws_security_group x3 (backend, infra, rds)
aws_instance x2 (t2.micro)
aws_db_instance x1 (db.t3.micro PostgreSQL)
aws_key_pair (SSH key)
aws_eip x2 (static IPs for EC2)

# Vercel
vercel_project
vercel_deployment
```

### 7. Docker Compose Files
- `docker-compose.backend.yml` — Core + TPS + Worker + Nginx
- `docker-compose.infra.yml` — Temporal + Temporal UI + PostgreSQL (for Temporal)
- `Dockerfile.backend` — Python services (multi-stage, slim)
- `Dockerfile.worker` — Worker (same base, different entrypoint)

### 8. Secrets Management
- Terraform variables for secrets (DB password, TPS secret, Fernet keys)
- Stored in `terraform.tfvars` (gitignored)
- Passed to EC2 via user data → .env file

## Resolved Questions

- **Q: t2.micro enough?** A: Yes with the split. Backend ~400MB, Infra ~700MB with swap.
- **Q: Temporal Cloud vs self-host?** A: Self-host for unlimited actions.
- **Q: CI/CD?** A: GitHub Actions + SSH deploy.
- **Q: Frontend hosting?** A: Vercel (free), managed via Terraform.
- **Q: Domain?** A: Not yet. Public IPs for now.

## File Structure

```
infra/
├── terraform/
│   ├── main.tf              # Provider config
│   ├── variables.tf         # Input variables
│   ├── vpc.tf               # VPC + subnets
│   ├── security_groups.tf   # SG rules
│   ├── ec2_backend.tf       # EC2 #1 + user data
│   ├── ec2_infra.tf         # EC2 #2 + user data
│   ├── rds.tf               # RDS PostgreSQL
│   ├── vercel.tf            # Vercel project
│   ├── outputs.tf           # IPs, endpoints
│   └── terraform.tfvars.example
│
├── docker/
│   ├── Dockerfile.backend   # Core + TPS
│   ├── Dockerfile.worker    # Temporal worker
│   └── nginx.conf           # Reverse proxy config
│
├── compose/
│   ├── docker-compose.backend.yml
│   └── docker-compose.infra.yml
│
└── .github/
    └── workflows/
        └── deploy.yml       # GitHub Actions CI/CD
```

## Next Steps

Run `/workflows:plan` to break this into implementation phases.
