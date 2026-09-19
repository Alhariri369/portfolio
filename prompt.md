# Build Prompt — Personal Portfolio (hariri-dev.com)

Read `requirements.md` in this repo first. It is the source of truth for scope
and decisions. This prompt contains the operative build instructions and the
seed content. Where they conflict, `requirements.md` wins.
daddy_tree
## Mission

Build a production-ready personal portfolio for Mohammed Alhariri, a backend
developer and fresh IT graduate, running on his own domain `hariri-dev.com`.
The site proves real backend ability: real experience, real projects, a
working contact form, bilingual EN/AR, and content he can edit through an
admin panel without touching code.

## Hard constraints

- Python 3.13, FastAPI, Jinja2, SQLAlchemy 2.x with a **sync** engine, Postgres
  (Neon free tier) in production, SQLite allowed for local dev, SQLAdmin,
  uvicorn. No async SQLAlchemy. Models must run on both backends — no
  Postgres-only column types.
- Server-rendered HTML only. No JS framework, no bundler. Vanilla JS limited
  to ~30 lines for nav/mobile menu and the scroll animations.
- No auth framework, no user accounts, no sessions on public pages.
  `/admin` is protected by a single HTTP Basic Auth credential from env vars.
- The whole deployment must be portable: one compose file, uploads in
  `./data`, all config in `.env` (including `DATABASE_URL`). The DB lives in
  Neon Postgres — never on the device — so restoring on any Linux host takes
  under an hour with no data migration, per the runbook in the README.
- Bilingual: English at `/`, Arabic at `/ar`, full RTL for Arabic. Every
  user-facing text column is stored twice (`*_en`, `*_ar`).
- The contact form must never send email for honeypot/rate-limited/spam
  submissions.
- No fake data. The `testimonial` table exists but the seed contains none;
  the section renders only when at least one published testimonial exists.
- Replace the current hello-world `main.py` with a proper `app/` package.
- Dependencies: minimal, pinned in `pyproject.toml` — fastapi, uvicorn,
  jinja2, sqlalchemy, psycopg (v3, binary), sqladmin, pydantic, python-multipart,
  resend, boto3, pytest. Do not add a web framework besides FastAPI, do not add
  celery/redis/etc.

## Deliverables (file tree)

```
app/
  __init__.py
  main.py            # FastAPI app, routes, middleware, static mount
  models.py          # SQLAlchemy models
  schemas.py         # Pydantic: ContactForm
  admin.py           # SQLAdmin setup + Basic Auth guard
  db.py              # engine, session, Base
  i18n.py            # translation loading + t() helper
  seed.py            # idempotent seed script (run: python -m app.seed)
  backup.py          # daily offsite backup to Cloudflare R2 (run: python -m app.backup)
  templates/
    base.html        # html head, nav, footer, fonts, meta
    index.html       # single-page home (all sections)
    project_detail.html
    errors/404.html, 429.html
  static/
    css/main.css
    js/main.js
    img/og.png       # placeholder OG image 1200x630
    uploads/         # avatar, banner, screenshots, resume PDF (Docker volume)
translations/en.json, ar.json
tests/
  test_contact.py
  test_i18n.py
  test_seed.py
Dockerfile
docker-compose.yml
.env.example
README.md            # full how-to-run — client explicitly requires this
pytest.ini or config in pyproject
```

## Data model (exact)

SQLAlchemy declarative models, `create_all` on startup (no Alembic). All
timestamps UTC. Snake_case columns.

- **Profile** (singleton, id=1): name, title_en, title_ar, tagline_en,
  tagline_ar, summary_en, summary_ar, location_en, location_ar, email, phone,
  github_url, avatar_url, banner_url, resume_pdf_url, og_image_url.
- **Skill**: name_en, name_ar, category, sort_order.
- **Experience**: company_en/ar, role_en/ar, location_en/ar, start_date (date),
  end_date (date, nullable), is_current (bool), description_en/ar (Text),
  sort_order.
- **Education**: institution_en/ar, degree_en/ar, field_en/ar, start_date,
  end_date, description_en/ar.
- **Certificate**: name_en/ar, issuer_en/ar, issue_date, url.
- **Project**: slug (unique), title_en/ar, summary_en/ar, description_en/ar,
  repo_url, live_url, featured (bool), sort_order. Many-to-many with Skill via
  `project_skill` table.
- **ProjectImage**: project_id (FK), url, alt_en, alt_ar, sort_order.
- **SocialLink**: platform, url, sort_order.
- **Testimonial**: author_en/ar, role_en/ar, text_en/ar, published (bool).
- **ContactMessage**: name, email, subject, body, created_at, is_spam (bool).

## Routes (exact)

- `GET /` and `GET /ar` — single-page home. Section order: hero, about, skills,
  experience, education, certificates, projects grid, testimonials
  (conditional), contact form. Nav = anchor links; on mobile, a collapsible menu.
- `GET /projects/{slug}` and `GET /ar/projects/{slug}` — project detail:
  gallery of all images, description, tech chips (skills), repo/live links when
  present, back link. 404 if slug unknown.
- `POST /contact` and `POST /ar/contact` — contact pipeline (below).
- `GET /sitemap.xml` — EN + AR URLs, absolute `https://hariri-dev.com`.
- `GET /robots.txt` — allow all, sitemap reference.
- `GET /healthz` — plain `ok` for Docker healthcheck.
- `/admin` — SQLAdmin, behind Basic Auth.

## Contact pipeline (exact order, no exceptions)

1. Parse form with Pydantic: name (1–100), email (valid, ≤254), subject
   (0–200), message (1–5000). On validation error re-render form with errors,
   keep entered values.
2. Honeypot: hidden input named `website` (CSS-hidden, `tabindex=-1`,
   autocomplete off). If non-empty → insert row with `is_spam=True`, redirect
   with `?sent=1` (fake success). **No email.**
3. Time-gate: hidden `loaded_at` unix timestamp rendered into the form. If
   `now - loaded_at < 2s` → treat as spam (same as step 2).
4. Rate limit: in-memory dict {ip: list of timestamps}, 3/hour. On exceed →
   render 429 page (same page, human message in the page language).
5. Insert `ContactMessage` with `is_spam=False`.
6. Send via Resend SDK: from `EMAIL_FROM` (default `portfolio@hariri-dev.com`)
   to `EMAIL_TO` (default `moh.alhariri369@gmail.com`), `reply_to` = visitor's
   email, subject `Portfolio contact: {subject}`, plain-text body containing
   name, email, subject, message. Wrap in try/except: log failure, keep the
   row, still redirect with `?sent=1`.
7. Redirect to the same page (`/` or `/ar`) with `?sent=1`; template shows the
   confirmation banner. No flash/session machinery — the query param is enough.

## i18n mechanics

- Load `translations/en.json` and `translations/ar.json` once at startup into
  dicts. Expose `t(key)` as a Jinja global; missing key → log a warning and
  return the key. Flat keys like `"nav.projects"`.
- Language = `ar` if `request.url.path` starts with `/ar` (also `/ar/...`),
  else `en`. Pass `lang` into every template render.
- `<html lang="{lang}" dir="rtl" if ar else "ltr">`. Arabic font family applied
  under `[dir="rtl"]` or an `.ar` class on `<html>`.
- UI strings go through `t()`; DB content picks `{field}_en` or `{field}_ar`
  by language. Helper Jinja function `pick(obj, "title")` is acceptable.
- Every page: `<link rel="alternate" hreflang>` pair (`/path` ↔ `/ar/path`),
  canonical to itself.
- Arabic translations in `ar.json` and all `*_ar` seed content must be
  idiomatic Modern Standard Arabic — translate properly, do not transliterate.

## Admin (SQLAdmin)

- Mount SQLAdmin at `/admin`; register models: Profile, Skill, Experience,
  Education, Certificate, Project, ProjectImage, SocialLink, Testimonial,
  ContactMessage.
- Use `FileField` for upload columns (avatar, banner, screenshots, resume PDF)
  writing to `app/static/uploads/`.
- Guard the whole `/admin` with HTTP Basic Auth: credentials from
  `ADMIN_USERNAME` / `ADMIN_PASSWORD` env (defaults `admin` / `change-me`);
  compare with `secrets.compare_digest`. No login page, no sessions — plain
  Basic Auth.
- ContactMessage rows visible in admin so the owner can review/delete them.

## Design system — Option A "Paper & Ink"

- Light only. Palette: bg `#FAF9F6`, surface `#FFFFFF`, ink `#1C2430`, muted
  `#5A6472`, accent teal `#2A9D8F`, hairline `#E5E2DC`. One accent only.
- Fonts via Google Fonts (preconnect): Manrope 400/600/700 (Latin),
  IBM Plex Sans Arabic 400/600/700 (Arabic), JetBrains Mono 400/600 (labels,
  dates, tech chips, small caps headers).
- Layout: max-width ~68rem, generous section padding, hairline dividers
  between sections, no gradients, no glassmorphism, no shadows heavier than
  `0 1px 2px rgba(28,36,48,.06)`.
- Section headers: mono uppercase label (e.g. `// experience`) + a large
  heading.
- Hero: avatar (rounded), name, title, tagline, CTAs: "Get in touch" (primary,
  anchor to contact), GitHub, resume PDF (if set). Banner image as a soft
  background strip if provided.
- Skills: grouped by category, simple chips or two-column lists.
- Experience/Education: timeline with hairline rail; dates in mono.
- Projects: grid of cards (first image, title, summary, mono tech chips).
  Featured project gets a subtle "featured" tag and sits first.
- Contact: form (name, email, subject, message, honeypot) + email/phone/
  GitHub links.
- Motion: sections fade/rise 8–12px on scroll via IntersectionObserver;
  `prefers-reduced-motion` disables all animation. Nothing else moves.
- Accessibility: WCAG 2.1 AA, contrast ≥ 4.5:1, skip link, visible focus
  styles, form labels, `alt` from `alt_en/alt_ar`, semantic landmarks
  (header/nav/main/section/footer).
- RTL: the entire layout must mirror correctly under `dir="rtl"` — check the
  timeline rail, paddings, and form alignment. Build it direction-agnostic
  (logical properties: `margin-inline-start`, not `margin-left`).

## SEO

- Per page + language: unique `<title>` and meta description, canonical,
  hreflang pair, OG (`og:title`, `og:description`, `og:image`, `og:url`,
  `og:type`, `og:locale` / `og:locale:alternate`) + Twitter card tags.
- JSON-LD: `Person` (name, jobTitle, email, url, sameAs GitHub) and `WebSite`
  on the home page; `hreflang` handling via links in head.
- `sitemap.xml`: `/`, `/ar`, `/projects/{slug}`, `/ar/projects/{slug}`.
- Images: WebP when possible, explicit `width`/`height`, `loading="lazy"`
  except hero/above-fold, descriptive alt.
- `/static` responses get long cache headers (e.g. 30 days); HTML never cached.
- Favicon (simple SVG + PNG fallback).
- Analytics: Cloudflare Web Analytics. In `base.html` head, render the beacon
  script ONLY when `CF_ANALYTICS_TOKEN` env is set:
  `<script defer src="https://static.cloudflareinsights.com/beacon.min.js"
data-cf-beacon='{"token": "..."}'>`. Token empty/missing → no script at all.
  No other analytics, no cookies.

## Seed data (from the owner's CV — EN given; you must provide idiomatic AR for every *_ar field)

profile: name `Mohammed Alhariri`; title `Backend Developer`; tagline `Backend
Developer and Information Technology graduate focused on Python, FastAPI, and
database management.`; location `Yemen`; email `moh.alhariri369@gmail.com`;
phone `+967 782 824 717`; github `https://github.com/alhariri369`.

experience:

1. role `Freelance Backend Developer`, company `Durrat Tarim`, location
   `Tarim, Yemen`, 2026-02 → 2026-03, description bullets:
   - Developed and deployed a custom web application for a retail client to digitize and manage their daily operations.
   - Built the backend using Django and integrated Supabase (PostgreSQL) for secure and reliable data storage.
   - Created a responsive UI with Tailwind CSS, working with the client to adjust the design based on their feedback.
2. role `Backend Developer`, company `Seiyun University`, location
   `Seiyun, Yemen`, 2026-01 → 2026-06, description bullets:
   - Built the backend for a proposal-checking and project-archiving platform used by students, supervisors, department heads, and admins end-to-end.
   - Quantized an ONNX version of multilingual MiniLM to 8-bit to fit Railway's 1GB RAM limit; semantic similarity search over a FAISS index kept in sync with Supabase via a local SQLite cache.
   - Built endpoints comparing a submitted proposal against completed projects and returning similarity scores, paired with Gemini-generated feedback.
   - Load-tested the API to confirm 300+ concurrent reads and 10 concurrent writes within Railway's hosting limits; built with FastAPI, SQLAlchemy, and Pydantic, using async where supported.
3. role `Python and Odoo Intern`, company `NOMOW-SOFT`, location `Yemen`,
   2025-01 → 2025-04, description: `Completed a technical training program
focused on Python and the basics of Odoo.`

education:

1. `Bachelor of Science in Information Technology`, `Seiyun University`,
   2022 → 2026.

certificates:

1. `Python Developer Certification` — `freeCodeCamp` — 2025-2026, no URL.
2. `Introduction to Generative AI` — `Google` — 2025-2026, no URL.

skills by category: Languages: Python. Frameworks: FastAPI, Django. Templating:
Jinja2. Data: SQLAlchemy, Pydantic, PostgreSQL, SQLite, Redis, Supabase.
AI / Vector search: FAISS, MiniLM (ONNX), Cosine Similarity. DevOps: Docker,
Git, GitHub.

projects:

1. slug `graduation-projects-platform`, featured `true`, title
   `Platform for Managing Graduation Projects`, summary `Proposal-checking and
project-archiving platform for students, supervisors, and admins.`,
   description = the 4 bullets from experience #2, skills = FastAPI, SQLAlchemy,
   Pydantic, Supabase, FAISS, MiniLM (ONNX) — add a skill `Gemini API` if not
   present. repo_url/live_url: null (owner fills later).
2. slug `durrat-tarim-retail-app`, featured `false`, title `Retail Operations
Web App`, summary `Custom web application digitizing daily operations for a
retail client.`, description = the 3 bullets from experience #1, skills =
   Django, Supabase, Tailwind CSS (create these skills). URLs null.

social_link: GitHub `https://github.com/alhariri369`.

Seed rules: idempotent — running twice leaves identical rows (upsert by natural
keys: slug, or name+category, etc.). Never seed testimonials. Never seed fake
project images or a fake resume PDF; those columns stay null.

## Deployment

- `Dockerfile`: `python:3.13-slim`, copy project, `pip install .`, install
  `postgresql-client` (needed by the backup container for `pg_dump`), expose
  8000, `CMD uvicorn app.main:app --host 0.0.0.0 --port 8000`. Non-root user.
- `docker-compose.yml`:
  - `app`: build ., `env_file: .env`, volume `./data:/data` (uploads live
    under `/data`; the DB is remote via `DATABASE_URL`), healthcheck
    `curl /healthz` (or python one-liner, no extra deps),
    `restart: unless-stopped`.
  - `cloudflared`: image `cloudflare/cloudflared:latest`, command
    `tunnel --no-autoupdate run --token ${CLOUDFLARE_TUNNEL_TOKEN}`,
    `restart: unless-stopped`. Tunnel points at `http://app:8000`.
  - `backup`: same image as the app, command `python -m app.backup`, shares
    the `./data` volume and uses `DATABASE_URL`, `restart: unless-stopped`.
    Script: run once on start, then every 24h — run `pg_dump` to a temp
    file, tar the dump + uploads dir, upload to R2 with a timestamped name
    (boto3, custom endpoint
    `https://<account_id>.r2.cloudflarestorage.com`), delete backups older
    than 30 days, log loudly on failure. When `DATABASE_URL` points at
    SQLite (local dev), skip the dump with a log line instead of failing.
- `.env.example` with comments: `ADMIN_USERNAME`, `ADMIN_PASSWORD`,
  `RESEND_API_KEY`, `EMAIL_FROM=portfolio@hariri-dev.com`,
  `EMAIL_TO=moh.alhariri369@gmail.com`, `CLOUDFLARE_TUNNEL_TOKEN`,
  `DATABASE_URL` (example placeholder
  `postgresql+psycopg://user:pass@ep-xxxx.neon.tech/dbname` — local dev may
  use `sqlite:///./app.db`), `UPLOAD_DIR=/data/uploads`,
  `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`,
  `CF_ANALYTICS_TOKEN` (optional — empty means no analytics beacon).
- Never hardcode secrets; never commit `.env`.

## Tests (pytest)

- Contact validation: missing/invalid fields re-render with errors.
- Honeypot filled → row saved with `is_spam=True`, no email call (mock the
  Resend client).
- Time-gate: `loaded_at` = now → spam path.
- Rate limit: 4th submission within the hour → 429.
- Valid submission → `is_spam=False`, email attempted, redirect has `sent=1`.
- i18n: every key in `en.json` exists in `ar.json` and vice versa; every `_en`
  seed field has a non-empty `_ar` counterpart (write a check that walks the
  seed data structure).
- Seed idempotency: run seed twice in a temp DB, assert row counts unchanged.
- Keep tests fast, no network.

## README.md (full how-to-run — the client explicitly requires this)

Sections, in order: What this is (1–2 lines) → Prerequisites (Docker + Docker
Compose, a Cloudflare account with the domain on it, a Resend account, a
Neon account) →
Step 1: clone, copy `.env.example` to `.env`, set `ADMIN_PASSWORD` →
Step 2: Neon — create a free Postgres project, copy the connection string
into `DATABASE_URL` (free tier autosuspends after ~5 min idle and wakes in
~1s; no keep-alive needed) →
Step 3: Resend — add domain `hariri-dev.com`, copy the SPF/DKIM records into
Cloudflare DNS, verify, create an API key, paste into `.env` →
Step 4: Cloudflare Tunnel — create a tunnel in Zero Trust dashboard for
`hariri-dev.com` → `http://localhost:8000`, copy the token into `.env`. The
owner already runs a tunnel for `terminal.hariri-dev.com`; he may add
`hariri-dev.com` as an ingress on that tunnel instead — same result. Also
create a Web Analytics site for `hariri-dev.com` (Analytics & Logs → Web
Analytics) and paste the beacon token into `CF_ANALYTICS_TOKEN` →
Step 5: `docker compose up -d --build` → Step 6: seed
(`docker compose exec app python -m app.seed`) → Step 7: open
`https://hariri-dev.com`, admin at `/admin`, **change the default admin
password** → Editing content (admin walkthrough: add project, upload images,
add testimonial) → Backups & disaster recovery: how the daily R2 backup
works (pg_dump + uploads), how to verify it, and the full runbook for when
the host PC dies — fresh Linux host or VPS: install Docker, clone the repo,
copy `.env`, download the latest backup into `./data`, `docker compose up
-d`, verify `https://hariri-dev.com` (the DB needs no restore — it lives in
Neon) → Troubleshooting: tunnel 502 (cloudflared logs), emails not arriving
(Resend domain verification, API key, check spam), Arabic text missing (seed
ran?), admin 401 (env creds), backups failing (R2 keys), DB connection
errors (Neon credentials).

## Acceptance criteria

- [ ] `docker compose up -d --build` then seed → site reachable locally on :8000 in EN and AR.
- [ ] AR pages render RTL and mirror layout correctly.
- [ ] Contact form: valid submit sends email (mockable), spam paths send nothing, 4th/hour → 429.
- [ ] `/admin` CRUD works after Basic Auth; uploads land in uploads dir.
- [ ] Testimonials hidden until one is published.
- [ ] `pytest` passes.
- [ ] Analytics beacon renders only when `CF_ANALYTICS_TOKEN` is set; nothing renders otherwise.
- [ ] Models and seed work on SQLite (dev) and Postgres/Neon (prod) with only `DATABASE_URL` changing.
- [ ] Backup container runs, uploads to R2, and the restore runbook works from an empty `./data`.
- [ ] sitemap + robots + hreflang + JSON-LD present and valid.
- [ ] README covers every step above.
- [ ] No fake content anywhere.

## Out of scope — do not build

Dark mode, blog, comments, user accounts, any JS framework, serverless
hosting (Vercel/Netlify/Workers — the app is a long-running FastAPI process),
async SQLAlchemy, Alembic, CAPTCHA, Celery/Redis, CI/CD, payments,
multi-tenant, realtime, Supabase in any form.

## Final message

After building: list files created/changed, exact run commands, decisions you
made that the requirements left open, and what the owner must still do himself
(provide screenshots/avatar/PDF, create Resend + tunnel tokens, a Neon
project, an R2 bucket + API keys, and the Cloudflare Web Analytics beacon
token, change admin password, review Arabic translations).
