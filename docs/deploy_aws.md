# Deploy the backend on AWS (EC2, Docker Compose, Caddy, HTTPS)

One EC2 instance runs the same Docker Compose stack as the Mac, plus Caddy, which gets a
Let's Encrypt certificate and is the only public entry point. SQLite stays in the
`backend_var` named volume. The backend serves the precomputed predictions in `artifacts/`
(`DATA_PROVIDER=artifacts`), which are copied to the server separately because they are
gitignored.

Data note: there is no automatic ingestion. The latest processed night is 2026-10-26; new
nights appear only after the ML pipeline runs on the Mac and `artifacts/` is synced again.
Live CDS ingestion is future work.

Files used here: `docker-compose.yml` (base), `docker-compose.prod.yml` (production
override: port 8000 not published, restart policy, proxy headers), `deploy/Caddyfile`,
`.env.production.example`, `deploy/scripts/*.sh`.

All commands below that start with `dc` use this alias on the server:

```bash
alias dc='docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile prod'
```

(Add it to `~/.bashrc` on the server.) Never run `dc config` without `--quiet`: it prints
the interpolated secrets.

## 1. Create the EC2 instance

In the AWS console, region **South America (São Paulo) sa-east-1**:

1. EC2 > Key pairs > Create key pair: name `frostwatch`, type ED25519, format `.pem`. Save it
   on the Mac and protect it:
   ```bash
   mv ~/Downloads/frostwatch.pem ~/.ssh/ && chmod 400 ~/.ssh/frostwatch.pem
   ```
2. EC2 > Security groups > Create security group `frostwatch-web`:
   - Inbound SSH (TCP 22) from **My IP** only.
   - Inbound HTTP (TCP 80) from `0.0.0.0/0` (needed for the Let's Encrypt challenge and the
     redirect to https).
   - Inbound HTTPS (TCP 443) from `0.0.0.0/0`, and optionally UDP 443 (HTTP/3).
   - Do not open 8000.
3. EC2 > Instances > Launch instance:
   - Name `frostwatch`, AMI **Ubuntu Server 24.04 LTS (64-bit x86)**, type **t3.small**.
   - Key pair `frostwatch`, security group `frostwatch-web`.
   - Storage: **20 GiB gp3**.
4. EC2 > Elastic IPs > Allocate Elastic IP address, then Actions > Associate with the
   `frostwatch` instance. Write down the address (below: `<EIP>`).

## 2. DNS

Option A, your own domain (Namecheap): Domain List > Manage > Advanced DNS > Add new record:
type **A Record**, host `frostwatch` (or another subdomain), value `<EIP>`, TTL automatic.
Your domain is then `frostwatch.<yourdomain>`. Check from the Mac:

```bash
dig +short frostwatch.<yourdomain>      # must print <EIP>
```

Option B, no domain yet: use `<EIP with dashes>.sslip.io`, for example `54-233-1-2.sslip.io`
for `54.233.1.2`. It resolves to the IP with no setup. If Let's Encrypt rate limits it, wait
or use your own domain.

## 3. Prepare the server

```bash
ssh -i ~/.ssh/frostwatch.pem ubuntu@<EIP>
git clone https://github.com/MarvinMR24/altiplano-frost-alert.git
cd altiplano-frost-alert
bash deploy/scripts/server_bootstrap.sh
exit                                      # log out so the docker group applies
```

The bootstrap installs Docker Engine and the compose plugin from Docker's official apt
repository, adds `ubuntu` to the `docker` group, creates a 2 GB swap file, enables
unattended security upgrades and the ufw firewall (22, 80, 443).

## 4. Upload the secrets and the artifacts (from the Mac, repo root)

```bash
cp .env.production.example .env.production      # once; then fill it in with an editor
openssl rand -base64 48                          # paste the output as SESSION_SECRET
deploy/scripts/sync_env.sh ubuntu@<EIP>          # becomes ~/altiplano-frost-alert/.env, mode 600
deploy/scripts/sync_artifacts.sh ubuntu@<EIP> --dry-run   # shows what would be copied
deploy/scripts/sync_artifacts.sh ubuntu@<EIP>
```

In `.env.production` set at least `APP_ENV=demo`, `DOMAIN` (no https://),
`PUBLIC_BASE_URL=https://<DOMAIN>`, `SESSION_SECRET`, `DATA_PROVIDER=artifacts`,
`MUSE_MOCK=0` with the Meta API settings and `MUSE_MAX_TOKENS=8000`, and
`EMAIL_PROVIDER=console`: login codes are printed in the server log
(`dc logs backend | grep -iE "codigo|código|code is"`), so on the demo server people sign in
with Google. `APP_ENV=production` would require real email (SMTP), which this project does
not use. For SSH with the key file,
add `-i` support with `ssh-add ~/.ssh/frostwatch.pem` before running the scripts.

## 5. Deploy and check

```bash
ssh -i ~/.ssh/frostwatch.pem ubuntu@<EIP>
cd altiplano-frost-alert
bash deploy/scripts/deploy.sh
```

It pulls the code, builds and starts backend and Caddy, prunes old images and waits for
`https://<DOMAIN>/health`. The first start takes a minute while Caddy gets the
certificate. From the Mac:

```bash
curl -s https://<DOMAIN>/health                  # {"status":"ok"}
curl -sI http://<DOMAIN>/health | head -1        # 308 redirect to https
curl -s -m 5 http://<EIP>:8000/health || echo "8000 closed (expected)"
```

## 6. Demo data and replay (inside the backend container)

```bash
dc exec backend python -m app.cli seed-demo --email <your-email>
dc exec backend python -m app.cli replay --night 2024-08-17 --email <your-email> --dry-run
dc exec backend python -m app.cli replay --night 2024-08-17 --email <your-email>
```

The replay writes the alert email to the server log (console email), sends an Expo push to
devices registered by that user,
with a Muse explanation (it is labeled as a replay).

## 7. Operate

Update after a new commit on `main`:

```bash
ssh -i ~/.ssh/frostwatch.pem ubuntu@<EIP> 'cd altiplano-frost-alert && bash deploy/scripts/deploy.sh'
```

New artifacts (after the ML pipeline ran on the Mac): `deploy/scripts/sync_artifacts.sh
ubuntu@<EIP>`; the backend reads new files without a restart.

Logs:

```bash
dc logs -f --tail 100 backend caddy
dc ps
```

Backups of the SQLite database (users, zones, alerts):

```bash
bash deploy/scripts/backup_db.sh          # writes ~/backups/frostwatch-<UTC time>.db, keeps 14
crontab -e                                # daily at 03:30 server time:
# 30 3 * * * cd $HOME/altiplano-frost-alert && bash deploy/scripts/backup_db.sh >> $HOME/backups/backup.log 2>&1
scp -i ~/.ssh/frostwatch.pem ubuntu@<EIP>:backups/frostwatch-*.db ~/Downloads/   # copy off the server
```

Google sign in (optional): in the Google Cloud OAuth client add the redirect URI
`https://<DOMAIN>/auth/google/callback` and set `GOOGLE_CLIENT_ID` and
`GOOGLE_CLIENT_SECRET` in `.env.production`, then `sync_env.sh` and `deploy.sh` again.

## Cost and how to stop

Rough monthly cost in sa-east-1 (check the AWS pricing calculator, prices change): the
t3.small instance running all month is in the order of 25 to 30 USD, the public IPv4 /
Elastic IP adds about 3.6 USD (0.005 USD per hour), and 20 GB of gp3 storage a few dollars.
Outbound traffic for this API is negligible. Set a billing alarm in AWS Budgets.

To stop paying:

- Pause: `dc down` stops the containers (data stays). Stopping the instance in the console
  ends the instance charge, but storage and the Elastic IP are still billed.
- Remove everything: take a last backup and copy it to the Mac, then in the console
  terminate the instance, release the Elastic IP (Elastic IPs > Release) and check that no
  EBS volume or snapshot is left (Volumes, Snapshots). Remove the DNS record.
