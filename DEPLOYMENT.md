# Deploying Schedulfy

Deploys to [Render](https://render.com): the Flask API as a Web Service, the
React app as a Static Site, and a managed Postgres database — all on free tiers.

---

## Why not Vercel or Netlify for the backend

Both are excellent for the React half, but neither suits this Flask app: they run
serverless functions, which conflict with the two things this backend needs —
server-side session cookies and a persistent database connection. Render runs the
API as an ordinary always-on process, so nothing about the app has to change.

You can still host the frontend on Vercel/Netlify if you prefer. See
[Frontend elsewhere](#optional-hosting-the-frontend-on-vercel-or-netlify).

---

## What changed for production

| Concern | Before | Now |
|---|---|---|
| Database | SQLite file | Postgres via `DATABASE_URL` (SQLite still the local default) |
| API URL | Hardcoded `localhost:5003` | `REACT_APP_API_URL` at build time |
| Session cookie | `SameSite=Lax`, `Secure=False` | `SameSite=None; Secure` when `FLASK_ENV=production` |
| Server | Flask dev server | gunicorn via `backend/wsgi.py` |
| `SECRET_KEY` | Fell back to a dev default | Boot fails in production if unset |

Local development is unchanged: with no `DATABASE_URL` and no `FLASK_ENV`, you get
SQLite and `Lax` cookies exactly as before.

---

## Deploy

### 1. Push to GitHub

```bash
git push origin main
```

### 2. Create the Blueprint

Render Dashboard → **New** → **Blueprint** → select this repo. Render reads
`render.yaml` and creates three resources: `schedulfy-db`, `schedulfy-api`,
`schedulfy-web`.

The first deploy will **partially fail**, which is expected — the two services
don't know each other's URLs yet. Fix that in step 3.

### 3. Set the environment variables

On **schedulfy-api** → Environment:

| Key | Value |
|---|---|
| `OPENAI_API_KEY` | your OpenAI key |
| `CORS_ORIGINS` | `https://schedulfy-web.onrender.com` |

On **schedulfy-web** → Environment:

| Key | Value |
|---|---|
| `REACT_APP_API_URL` | `https://schedulfy-api.onrender.com` |

Use your actual Render URLs if the service names differ. **No trailing slashes** —
`api.js` appends `/api` itself.

`SECRET_KEY` and `DATABASE_URL` are set automatically by the blueprint.

### 4. Redeploy both services

Manual Deploy → **Deploy latest commit**, on each service.

`REACT_APP_API_URL` is baked in at build time, so the frontend **must** be rebuilt
after changing it — restarting is not enough.

### 5. Verify

```bash
curl https://schedulfy-api.onrender.com/api/health
```

Expect `{"status":"healthy","ai_enabled":true,...}`. Then open the frontend, sign
up, and confirm you stay logged in after a refresh.

---

## Notes and limits

**Free tier sleeps.** The API spins down after 15 minutes idle; the next request
takes ~30 seconds. If you're demoing live, hit the health endpoint first to wake it.

**Free Postgres expires after 30 days.** Render deletes free databases at 30 days.
For anything longer-lived, either upgrade the database or point `DATABASE_URL` at a
free tier without that limit ([Neon](https://neon.tech), [Supabase](https://supabase.com)).
Nothing in the app changes — it's one environment variable.

**First boot seeds the database.** `wsgi.py` calls `init_db()`, which creates the
tables and loads the sample catalog if the `course` table is empty. Existing data
is never overwritten.

**One worker.** The API runs `--workers 1 --threads 4`. The course-similarity index
is per-process in-memory state, and the 512 MB free tier can't hold multiple copies
of pandas + scikit-learn anyway.

**No migration tooling.** Schema changes rely on `db.create_all()`, which creates
missing tables but never alters existing ones. If you change a model's columns,
add Flask-Migrate or recreate the table manually.

---

## Optional: hosting the frontend on Vercel or Netlify

Drop the `schedulfy-web` service from `render.yaml` and:

- **Root directory**: `frontend`
- **Build command**: `npm run build`
- **Publish directory**: `build`
- **Environment**: `REACT_APP_API_URL=https://schedulfy-api.onrender.com`, and `CI=false`
- **SPA rewrite**: Vercel handles CRA automatically. For Netlify, add
  `frontend/public/_redirects` containing `/*  /index.html  200`.

Then update `CORS_ORIGINS` on the API to the new frontend origin and redeploy it.

---

## Troubleshooting

**Build fails on lint warnings** — CRA treats warnings as errors when `CI=true`,
which is Render's default. `render.yaml` sets `CI=false`. This codebase has ~20
unused-import warnings, so without that flag the build fails.

**Build fails compiling numpy or psycopg2** — `PYTHON_VERSION` isn't set to
`3.11.9`. Those pinned versions have no wheels for Python 3.13 and fall back to
compiling from source.

**Login succeeds but you're logged out on refresh** — the session cookie is being
dropped. Check `FLASK_ENV=production` is set on the API (that's what switches the
cookie to `SameSite=None; Secure`), and that `CORS_ORIGINS` exactly matches the
frontend origin including `https://`.

**CORS errors in the browser console** — `CORS_ORIGINS` doesn't match the frontend
origin exactly. It's a comma-separated list; scheme must be included and there must
be no trailing slash.

**AI features return errors** — `OPENAI_API_KEY` is missing or out of credit.
`/api/health` reports `ai_enabled` but doesn't validate the key.
