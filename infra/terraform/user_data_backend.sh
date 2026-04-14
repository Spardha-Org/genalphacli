#!/bin/bash
set -euo pipefail

# ── Install Docker ──
yum update -y
yum install -y docker git postgresql16
systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user

# Install Docker Compose
DOCKER_COMPOSE_VERSION="v2.29.1"
curl -L "https://github.com/docker/compose/releases/download/$${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# ── Add 1GB swap ──
dd if=/dev/zero of=/swapfile bs=1M count=1024
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile swap swap defaults 0 0' >> /etc/fstab

# ── Create app directory ──
mkdir -p /opt/genalpha
cd /opt/genalpha

# ── Write .env file ──
cat > .env << 'ENVEOF'
# Core Service
CORE_DATABASE__URL=postgresql+asyncpg://${db_user}:${db_password}@${db_host}:${db_port}/core
CORE_AUTH__MAGIC_LINK_SECRET=${magic_link_secret}
CORE_AUTH__SESSION_COOKIE_SECURE=false
CORE_TPS__URL=http://localhost:8001
CORE_TPS__SECRET=${tps_secret}
CORE_WORKER__SECRET=${worker_secret}
CORE_APP_URL=${app_url}
CORE_TEMPORAL_ADDRESS=${temporal_host}:7233
CORE_EMAIL__RESEND_API_KEY=${resend_api_key}

# TPS Service
TPS_DATABASE_URL=postgresql+asyncpg://${db_user}:${db_password}@${db_host}:${db_port}/tps
TPS_TPS_SECRET=${tps_secret}
TPS_FERNET_KEYS=${fernet_key}

# Worker
CORE_URL=http://localhost:8000
TPS_URL=http://localhost:8001
TPS_SECRET=${tps_secret}
WORKER_SECRET=${worker_secret}
TEMPORAL_ADDRESS=${temporal_host}:7233
ENVEOF

# ── Create databases on RDS ──
export PGPASSWORD="${db_password}"
psql -h ${db_host} -p ${db_port} -U ${db_user} -d genalpha -c "SELECT 1 FROM pg_database WHERE datname='core'" | grep -q 1 || \
  psql -h ${db_host} -p ${db_port} -U ${db_user} -d genalpha -c "CREATE DATABASE core"
psql -h ${db_host} -p ${db_port} -U ${db_user} -d genalpha -c "SELECT 1 FROM pg_database WHERE datname='tps'" | grep -q 1 || \
  psql -h ${db_host} -p ${db_port} -U ${db_user} -d genalpha -c "CREATE DATABASE tps"

# ── Clone repo and start services ──
git clone https://github.com/Spardha-Org/genalphacli.git repo
cd repo

# Start backend services
docker-compose -f infra/compose/docker-compose.backend.yml --env-file /opt/genalpha/.env up -d

echo "Backend setup complete" > /opt/genalpha/setup.log
