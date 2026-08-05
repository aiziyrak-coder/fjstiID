"""
FJSTI ID → server deploy (id.fermi.uz).
Boshqa nginx saytlarga / docker stacklarga tegmaydi.
"""
from __future__ import annotations

import io
import os
import os
import sys
import tarfile
import time
from pathlib import Path

import paramiko

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
_SECRETS = Path(__file__).resolve().parent / ".secrets"
if _SECRETS.exists():
    for line in _SECRETS.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

HOST = os.environ.get("FJSTI_DEPLOY_HOST", "87.192.230.208")
PORT = int(os.environ.get("FJSTI_DEPLOY_PORT", "2222"))
USER = os.environ.get("FJSTI_DEPLOY_USER", "admin_root")
PASS = os.environ.get("FJSTI_DEPLOY_PASS", "")
REMOTE_DIR = "/home/admin_root/fjsti-id"
WWW_DIR = "/var/www/id.fermi.uz"
NGINX_AVAIL = "/etc/nginx/sites-available/id.fermi.uz"
NGINX_ENABLED = "/etc/nginx/sites-enabled/id.fermi.uz"

EXCLUDE_DIRS = {
    "node_modules",
    ".git",
    ".venv",
    "__pycache__",
    "dist",
    ".idea",
    ".vscode",
    "uploads",
    "agent-transcripts",
}
EXCLUDE_FILES = {".demo_api_key", "test_face.jpg"}


def connect() -> paramiko.SSHClient:
    if not PASS:
        raise SystemExit("FJSTI_DEPLOY_PASS yo'q — deploy/.secrets yoki env o'rnating")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30, allow_agent=False, look_for_keys=False)
    return c


def run(c: paramiko.SSHClient, cmd: str, check: bool = True, timeout: int = 1800) -> str:
    print(f"$ {cmd}")
    _, stdout, stderr = c.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    rc = stdout.channel.recv_exit_status()
    if out:
        print(out[-4000:] if len(out) > 4000 else out)
    if err.strip():
        print(err[-2000:] if len(err) > 2000 else err)
    if check and rc != 0:
        raise RuntimeError(f"Command failed ({rc}): {cmd}")
    return out


def sudo(c: paramiko.SSHClient, cmd: str, **kw) -> str:
    probe = run(c, "sudo -n true && echo SUDO_OK || echo SUDO_NEED_PASS", check=False)
    if "SUDO_OK" in probe:
        return run(c, f"sudo -n bash -lc {repr(cmd)}", **kw)
    safe = cmd.replace("'", "'\"'\"'")
    full = f"printf '%s\\n' '{PASS}' | sudo -S -p '' bash -lc '{safe}'"
    return run(c, full, **kw)


def make_tarball() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT).as_posix()
            parts = set(Path(rel).parts)
            if parts & EXCLUDE_DIRS:
                continue
            if path.name in EXCLUDE_FILES:
                continue
            if path.name.endswith(".pyc"):
                continue
            # skip huge local-only noise
            if "frontend/node_modules" in rel:
                continue
            tar.add(path, arcname=f"fjsti-id/{rel}")
    data = buf.getvalue()
    print(f"Tarball size: {len(data) / 1024 / 1024:.1f} MB")
    return data


def sftp_write(c: paramiko.SSHClient, remote_path: str, data: bytes) -> None:
    sftp = c.open_sftp()
    try:
        with sftp.file(remote_path, "wb") as f:
            f.write(data)
    finally:
        sftp.close()


def sftp_put_file(c: paramiko.SSHClient, local: Path, remote: str) -> None:
    sftp = c.open_sftp()
    try:
        sftp.put(str(local), remote)
    finally:
        sftp.close()


def main() -> None:
    print("=== 1) Build frontend locally ===")
    frontend = ROOT / "frontend"
    env_prod = frontend / ".env.production"
    env_prod.write_text("VITE_API_URL=\n", encoding="utf-8")
    # build
    import subprocess

    subprocess.check_call(["npm", "ci"], cwd=str(frontend), shell=True)
    subprocess.check_call(["npm", "run", "build"], cwd=str(frontend), shell=True)
    dist = frontend / "dist"
    if not (dist / "index.html").exists():
        raise SystemExit("frontend dist missing")

    print("=== 2) Pack & upload ===")
    c = connect()
    run(c, f"mkdir -p {REMOTE_DIR} /tmp/fjsti-upload")
    tarball = make_tarball()
    sftp_write(c, "/tmp/fjsti-upload/fjsti-id.tar.gz", tarball)
    run(c, f"rm -rf {REMOTE_DIR}.bak && (test -d {REMOTE_DIR} && mv {REMOTE_DIR} {REMOTE_DIR}.bak || true)")
    run(c, f"mkdir -p {REMOTE_DIR} && tar -xzf /tmp/fjsti-upload/fjsti-id.tar.gz -C /home/admin_root && ls {REMOTE_DIR}")

    # upload frontend dist separately (included in tarball if built before pack — rebuild order)
    # Re-upload dist to be sure
    print("=== 3) Upload frontend dist ===")
    run(c, "rm -rf /tmp/fjsti-dist && mkdir -p /tmp/fjsti-dist")
    dist_buf = io.BytesIO()
    with tarfile.open(fileobj=dist_buf, mode="w:gz") as tar:
        for p in dist.rglob("*"):
            if p.is_file():
                tar.add(p, arcname=p.relative_to(dist).as_posix())
    sftp_write(c, "/tmp/fjsti-dist.tar.gz", dist_buf.getvalue())
    sudo(c, f"mkdir -p {WWW_DIR} && rm -rf {WWW_DIR}/* && tar -xzf /tmp/fjsti-dist.tar.gz -C {WWW_DIR} && chown -R www-data:www-data {WWW_DIR}")

    print("=== 4) Ensure .env.production on server ===")
    env_local = ROOT / "backend" / ".env.production"
    if env_local.exists():
        sftp_put_file(c, env_local, f"{REMOTE_DIR}/backend/.env.production")

    print("=== 5) Docker compose up (localhost binds only) ===")
    run(
        c,
        f"cd {REMOTE_DIR}/deploy && "
        f"POSTGRES_PASSWORD='FjstiDb_Prod_2026!' docker compose -f docker-compose.prod.yml --project-name fjstiid "
        f"up -d --build",
        timeout=2400,
    )

    print("=== 6) Wait API health ===")
    for i in range(60):
        out = run(c, "curl -sf http://127.0.0.1:8120/health || true", check=False)
        if '"status"' in out and "ok" in out:
            print("API healthy")
            break
        time.sleep(5)
    else:
        run(c, "docker logs fjstiid-api --tail 80", check=False)
        raise RuntimeError("API did not become healthy")

    print("=== 7) Seed (org + staff + students from uploaded JSON) ===")
    run(c, "docker exec fjstiid-api python -m app.seed", timeout=3600)

    print("=== 8) Nginx site ONLY for id.fermi.uz ===")
    # Write nginx config via temp then sudo move — do not touch other configs
    nginx_src = (ROOT / "deploy" / "nginx.id.fermi.uz.conf").read_text(encoding="utf-8")
    # HTTP-only first for certbot if no cert yet
    http_only = """server {
    listen 80;
    server_name id.fermi.uz;
    client_max_body_size 30m;
    root /var/www/id.fermi.uz;
    index index.html;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8120;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location /oauth/ { proxy_pass http://127.0.0.1:8120; proxy_set_header Host $host; proxy_set_header X-Forwarded-Proto $scheme; proxy_set_header X-Real-IP $remote_addr; proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; }
    location /.well-known/openid-configuration { proxy_pass http://127.0.0.1:8120; proxy_set_header Host $host; }
    location /.well-known/jwks.json { proxy_pass http://127.0.0.1:8120; proxy_set_header Host $host; }
    location /health { proxy_pass http://127.0.0.1:8120; }
    location /media/ { proxy_pass http://127.0.0.1:8120; proxy_set_header Host $host; }
    location /docs { proxy_pass http://127.0.0.1:8120; proxy_set_header Host $host; }
    location /openapi.json { proxy_pass http://127.0.0.1:8120; proxy_set_header Host $host; }
    location / { try_files $uri $uri/ /index.html; }
}
"""
    sftp = c.open_sftp()
    with sftp.file("/tmp/id.fermi.uz.nginx", "w") as f:
        f.write(http_only)
    sftp.close()

    # If old id.fermi.uz exists, backup then replace ONLY that file
    sudo(
        c,
        f"if [ -f {NGINX_AVAIL} ]; then cp {NGINX_AVAIL} {NGINX_AVAIL}.bak.$(date +%s); fi; "
        f"cp /tmp/id.fermi.uz.nginx {NGINX_AVAIL}; "
        f"ln -sfn {NGINX_AVAIL} {NGINX_ENABLED}; "
        f"nginx -t && systemctl reload nginx",
    )

    print("=== 9) SSL certbot (only id.fermi.uz) ===")
    # If cert exists, install SSL into config; else obtain
    out = run(c, "sudo -n ls /etc/letsencrypt/live/id.fermi.uz/fullchain.pem 2>/dev/null || printf '%s\\n' '" + PASS + "' | sudo -S ls /etc/letsencrypt/live/id.fermi.uz/fullchain.pem 2>/dev/null || true", check=False)
    if "fullchain.pem" not in out:
        sudo(
            c,
            "certbot --nginx -d id.fermi.uz --non-interactive --agree-tos -m admin@fjsti.uz --redirect || "
            "certbot certonly --webroot -w /var/www/certbot -d id.fermi.uz --non-interactive --agree-tos -m admin@fjsti.uz",
            timeout=300,
        )
    # Ensure SSL server block is present after certbot
    has_ssl = run(c, f"grep -n 'listen 443' {NGINX_AVAIL} || true", check=False)
    if "443" not in has_ssl:
        # Write full SSL config using existing cert path if certbot created it
        ssl_conf = nginx_src.replace(
            "# SSL filled/managed by certbot (or copied from existing)",
            """ssl_certificate /etc/letsencrypt/live/id.fermi.uz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/id.fermi.uz/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;""",
        )
        sftp = c.open_sftp()
        with sftp.file("/tmp/id.fermi.uz.nginx.ssl", "w") as f:
            f.write(ssl_conf)
        sftp.close()
        sudo(c, f"cp /tmp/id.fermi.uz.nginx.ssl {NGINX_AVAIL} && nginx -t && systemctl reload nginx")

    print("=== 10) Smoke test ===")
    run(c, "curl -sI http://127.0.0.1:8120/health | head -5")
    run(c, "curl -skI https://id.fermi.uz/health | head -15", check=False)
    run(c, "curl -skI https://id.fermi.uz/ | head -15", check=False)
    run(c, "docker ps --filter name=fjstiid --format '{{.Names}} {{.Status}} {{.Ports}}'")

    # Confirm other nginx sites untouched count
    run(c, "ls /etc/nginx/sites-enabled | wc -l; ls /etc/nginx/sites-enabled | grep -E 'fermi|fjsti|anylang|healthrisk' | head")

    c.close()
    print("=== DONE: https://id.fermi.uz ===")


if __name__ == "__main__":
    main()
