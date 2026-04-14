#!/bin/bash
set -euo pipefail

# ── Install Docker ──
yum update -y
yum install -y docker git
systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user

# Install Docker Compose
DOCKER_COMPOSE_VERSION="v2.29.1"
curl -L "https://github.com/docker/compose/releases/download/$${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# ── Add 1GB swap (Temporal needs it on t2.micro) ──
dd if=/dev/zero of=/swapfile bs=1M count=1024
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile swap swap defaults 0 0' >> /etc/fstab

# ── Create app directory ──
mkdir -p /opt/genalpha
cd /opt/genalpha

# ── Clone repo and start Temporal ──
git clone https://github.com/Spardha-Org/genalphacli.git repo
cd repo

docker-compose -f infra/compose/docker-compose.infra.yml up -d

echo "Infra setup complete" > /opt/genalpha/setup.log
