#!/usr/bin/env bash
# One-time setup of a fresh Ubuntu 24.04 EC2 instance. Run ON THE SERVER:
#   bash deploy/scripts/server_bootstrap.sh
# Installs Docker Engine and the compose plugin from Docker's apt repository, adds the
# user to the docker group, creates a 2 GB swap file, enables unattended security upgrades
# and the ufw firewall (22, 80, 443). Log out and in afterwards.
set -euo pipefail

if [[ "$(id -u)" -eq 0 ]]; then
  echo "run as the normal user (ubuntu), not root; sudo is used where needed" >&2
  exit 1
fi

echo "== Docker Engine (official repository)"
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${UBUNTU_CODENAME:-$VERSION_CODENAME} stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin rsync git
sudo usermod -aG docker "$USER"
sudo systemctl enable --now docker

echo "== 2 GB swap (t3.small has 2 GB RAM; image builds need headroom)"
if ! swapon --show | grep -q /swapfile; then
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab > /dev/null
fi

echo "== Unattended security upgrades"
sudo apt-get install -y unattended-upgrades
sudo dpkg-reconfigure -f noninteractive unattended-upgrades

echo "== Firewall (ufw): SSH, HTTP, HTTPS"
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 443/udp
sudo ufw --force enable

echo "== Done. Log out and back in so the docker group applies, then run deploy/scripts/deploy.sh"
