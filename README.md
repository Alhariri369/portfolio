# Mohammed Alhariri — Portfolio (hariri-dev.com)

A production-ready, bilingual (English/Arabic) personal portfolio for backend
developer Mohammed Alhariri. It is a long-running FastAPI process with a
Postgres database, a working contact form, and an admin panel for editing
content without touching code.

---

## Prerequisites

- Docker and Docker Compose (Linux host, or Docker Desktop on macOS/Windows)
- A Cloudflare account with `hariri-dev.com` on it (DNS + Tunnel + optional Web Analytics)
- A Resend account (for the contact-form email)
- A Neon account (free Postgres database)

---

## Step 1 — Clone and configure

```bash
git clone <your-repo-url> portfolio
cd portfolio
cp .env.example .env
```

Edit `.env` and set at least `ADMIN_PASSWORD`. Every other value is filled in
during the steps below. Never commit `.env`.

---

## Step 2 — Neon (the database)

1. Create a free Neon project (https://neon.tech).
2. Create a database, then copy the **connection string**.
3. Paste it into `.env`:

```dotenv
DATABASE_URL=postgresql+psycopg://user:password@ep-xxxx.neon.tech/dbname?sslmode=require
```

Notes:

- The Neon free tier **autosuspends** after ~5 minutes idle and wakes in ~1s.
  No keep-alive is needed.
- The database always lives in Neon — never on the host device. That is what
  makes disaster recovery a "clone + `.env` + compose up" job (see below).

For **local development only** you may use SQLite instead:

```dotenv
DATABASE_URL=sqlite:///./app.db
```

The exact same models and seed run on both backends.

---

## Step 3 — Resend (contact email)

1. Create a free Resend account (https://resend.com).
2. Add the domain `hariri-dev.com` in Resend.
3. Copy the **SPF** and **DKIM** records Resend shows you into Cloudflare DNS
   (DNS → Records) and wait for Resend to mark the domain **Verified**.
4. Create an **API key** in Resend and paste it into `.env`:

```dotenv
RESEND_API_KEY=re_xxxxxxxxxxxx
```

`EMAIL_FROM` and `EMAIL_TO` already default to the owner's addresses in
`.env.example`. The contact form replies to the visitor's address.

---

## Step 4 — Cloudflare Tunnel + Web Analytics

### Tunnel

The site is served by `cloudflared` from the Docker Compose stack, so the host
PC does not need a public IP or open ports.

Option A — new tunnel (used by the included `cloudflared` service):

1. In Cloudflare **Zero Trust → Networks → Tunnels**, create a tunnel.
2. Public hostname: `hariri-dev.com` → service `http://app:8000`.
3. Copy the **token** into `.env`:

```dotenv
CLOUDFLARE_TUNNEL_TOKEN=eyJ...
```

Option B — reuse the existing `terminal.hariri-dev.com` tunnel:

The owner already runs a Cloudflare tunnel for `terminal.hariri-dev.com`. You
can add `hariri-dev.com` as a second public hostname (ingress) on that tunnel
pointing at `http://localhost:8000` (or `http://app:8000` inside this stack)
and then you do **not** need the `cloudflared` service here. The end result is
identical.

### Web Analytics (optional)

1. Cloudflare **Analytics & Logs → Web Analytics → Add a site**.
2. Enter `hariri-dev.com` and copy the **beacon token**.
3. Paste it into `.env`:

```dotenv
CF_ANALYTICS_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

If `CF_ANALYTICS_TOKEN` is empty, no analytics script is rendered at all.

---

## Step 5 — Build and run

```bash
docker compose up -d --build
```

The stack starts three containers: `app` (FastAPI), `cloudflared` (tunnel), and
`backup` (daily offsite backup to R2).

Check that it is healthy:

```bash
docker compose ps
curl http://localhost:8000/healthz   # prints "ok"
```

---

## Step 6 — Seed the content

```bash
docker compose exec app python -m app.seed
```

The seed is idempotent — running it again leaves identical rows. It loads the
owner's real CV (profile, skills, experience, education, certificates, projects,
and the GitHub social link) in both English and Arabic.

---

## Step 7 — Open the site

- English: `https://hariri-dev.com/`
- Arabic: `https://hariri-dev.com/ar` (full RTL)
- Admin: `https://hariri-dev.com/admin`

Log in to `/admin` with `ADMIN_USERNAME` / `ADMIN_PASSWORD` (HTTP Basic Auth).
**Change the default admin password** by editing `.env` and restarting:

```bash
docker compose up -d --build
```

---

## Editing content (admin walkthrough)

All public content is edited in `/admin` — no code changes needed.

- **Profile** — update the singleton row (id 1). Upload an avatar, banner, and
  resume PDF via the file fields; they land in `/data/uploads` and are served
  at `/uploads/<filename>`.
- **Skills** — add/remove skills and set a `sort_order`; the home page groups
  them by `category`.
- **Experience / Education / Certificates** — edit the bilingual fields
  (`*_en` and `*_ar`). Dates are shown in monospace.
- **Projects** — create a project, give it a unique `slug`, mark `featured`
  to pin it first, and assign skills. Add screenshots under **ProjectImage**
  (choose the parent project, upload an image, set `alt_en` / `alt_ar`).
- **Testimonials** — the testimonials section only renders when at least one
  row has `published` checked. The seed intentionally contains none.
- **ContactMessage** — review incoming messages, then delete them.

---

## Backups & disaster recovery

### How backups work

The `backup` container runs `python -m app.backup` once on start, then every
24 hours. For a Postgres `DATABASE_URL` it:

1. runs `pg_dump` to a temp file,
2. tars the dump plus `/data/uploads`,
3. uploads the archive to Cloudflare R2 with a timestamped name,
4. deletes R2 backups older than 30 days.

Set these in `.env` (R2 bucket + API keys from the R2 dashboard):

```dotenv
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET=portfolio-backups
```

When `DATABASE_URL` points at SQLite (local dev) the dump step is skipped and a
log line is printed instead of failing.

### Verify a backup

```bash
docker compose logs backup
```

You should see "Upload complete". In the R2 dashboard, confirm a
`backup-<timestamp>.tar.gz` object exists.

### Full runbook — the host PC dies

The database was never on the device, so there is **no database to restore**.
To be back online on any fresh Linux host (or VPS) in under an hour:

1. Install Docker and Docker Compose.
2. `git clone <your-repo-url> portfolio && cd portfolio`
3. `cp .env.example .env` and paste the **same** values (Neon URL, Resend key,
   tunnel token, R2 keys, admin password).
4. Restore the uploads: download the latest backup from R2 and extract just the
   `uploads` directory into `./data`:

   ```bash
   mkdir -p data
   tar -xzf backup-<timestamp>.tar.gz -C data uploads
   ```

5. `docker compose up -d --build`
6. Open `https://hariri-dev.com` and confirm both languages load, then check
   `/admin` and the contact form.

The tunnel token moves with `.env`, so `cloudflared` reconnects to the same
tunnel. If the R2 backup contains no uploads yet, the site still works — only
uploaded images/PDFs would be missing until the owner re-adds them.

---

## Troubleshooting

| Symptom | Likely fix |
| --- | --- |
| Tunnel shows **502 Bad Gateway** | The `app` container is not reachable from `cloudflared`. Check `docker compose ps` and `docker compose logs app`. The tunnel public hostname must point at `http://app:8000`. |
| Emails are not arriving | Confirm the Resend domain is **Verified** (SPF/DKIM records in Cloudflare DNS), the API key is set, and check the recipient's spam folder. See `docker compose logs app` for send errors. |
| Arabic text is missing | The seed has not run (or was run against a different database). Run `docker compose exec app python -m app.seed`. |
| Admin returns **401** | You are using the wrong Basic Auth credentials. Check `ADMIN_USERNAME` / `ADMIN_PASSWORD` in `.env` and restart the stack. |
| Backups are failing | Check `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, and `R2_BUCKET` in `.env`. See `docker compose logs backup`. |
| Database connection errors | Verify the Neon connection string in `DATABASE_URL` (user, password, host, dbname, `?sslmode=require`). Neon autosuspends after idle but wakes in ~1s. |
| `/admin` uploads do not appear on the site | Uploads are stored under `/data/uploads` and served at `/uploads/<filename>`. Confirm `UPLOAD_DIR=/data/uploads` and the `./data` volume is mounted. |

---

## Local development (without Docker)

```bash
python -m venv .venv
.venv/bin/pip install -e .          # or: pip install -e .
DATABASE_URL=sqlite:///./app.db \
  .venv/bin/python -m app.seed
DATABASE_URL=sqlite:///./app.db \
  .venv/bin/uvicorn app.main:app --reload --port 8000
```

Run the tests (fast, no network):

```bash
.venv/bin/pytest
```
