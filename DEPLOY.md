# Deployment Guide — Priority Planner on Railway

This file lives with the code so the deploy steps are always at hand.

---

## Before you deploy — one-time setup

### 1. Get a Railway account

Sign up at [railway.app](https://railway.app). The free tier is enough to start.

### 2. Connect your GitHub

Railway deploys from GitHub. Push this project to a GitHub repo (public or private), then connect that repo to a Railway project.

### 3. Verify the project structure

These files MUST be in the project root for Railway to recognize the app:

| File | Purpose |
|---|---|
| `app.py` | The Flask entry point (Railway needs `app:app`) |
| `requirements.txt` | Python dependencies Railway installs |
| `Procfile` | The command Railway runs to start the app |
| `runtime.txt` | Pins Python to 3.11.10 |

If any are missing, the deploy will fail or behave oddly.

---

## The actual deploy

### Step 1 — Create a new Railway project

From your Railway dashboard:
1. Click **New Project**
2. Choose **Deploy from GitHub repo**
3. Select the Priority Planner repo

Railway will start building immediately. The first build takes ~1-2 minutes.

### Step 2 — Set the FLASK_SECRET_KEY environment variable

**This is critical.** Without it, the app generates a new random key on every restart, which invalidates all active sessions.

In the Railway project:
1. Click **Variables**
2. Click **+ New Variable**
3. Set:
   - **Key:** `FLASK_SECRET_KEY`
   - **Value:** a random 32+ character string (see below for how to generate one)

To generate a good secret key, run this locally:

```
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and paste it as the value. **Do not commit this key to git** — it lives in Railway's environment variables only.

### Step 3 — Verify the deploy worked

After Railway shows "Deployment successful":

1. Click **Settings** → **Domains** → **Generate Domain**
2. Railway gives you a URL like `https://your-app.up.railway.app`
3. Visit that URL — you should see the welcome page
4. Visit `https://your-app.up.railway.app/health` — should say `OK`

If both load, the app is live.

### Step 4 — Smoke test the full flow

In your browser on the deployed URL:

1. Click **Start with Signal events** on the welcome page
2. Enter one event (e.g. `Therapy | Monday | 4:00PM | 5:00PM`)
3. Click **Save and continue**
4. Skip through the other quadrants
5. On the review screen, verify your event is shown
6. Click **Looks good — show my timesheet**
7. Verify the timesheet renders
8. Click **Download as .txt** — file should download

If all eight steps work, the app is fully functional on Railway.

---

## What Railway does automatically

| Thing | Handled by |
|---|---|
| Python 3.11.10 installation | `runtime.txt` |
| Installing Flask and gunicorn | `requirements.txt` |
| Starting the server | `Procfile` (`gunicorn app:app --bind 0.0.0.0:$PORT ...`) |
| Setting `$PORT` | Railway injects it; the Procfile uses it |
| HTTPS / TLS termination | Railway terminates HTTPS at the edge; the app sees HTTP |
| Health checks | Railway polls `/health` and restarts if it stops responding |

---

## What's NOT handled and you should know about

### No persistent storage

Sessions are stored in signed cookies on the user's browser. They survive across restarts on the SAME browser. But:

- Railway's file system is ephemeral; never write files there expecting them to persist
- The CLI's `outputs/` folder doesn't apply to the web app — downloads stream directly to the user's browser

### No rate limiting

Railway has some platform-level DDoS protection at the edge, but there's no application-level rate limiting. If you start seeing abusive traffic, add Flask-Limiter (with Redis for multi-worker support) as a follow-up.

### Session size limit

Flask sessions live in cookies (~4 KB max). For a typical week (under ~60 events) this is plenty. If a user enters 90+ long-titled events, the cookie may hit the size ceiling. Engine input caps make this unlikely, but worth knowing.

### Logs

Railway shows you stdout/stderr logs in the dashboard. The app doesn't currently do structured logging — if errors happen in production, the logs will show Flask's standard tracebacks. **Stack traces never reach the user** because the custom 500 page strips them, but you can see them in Railway's log view.

---

## Re-deploying after changes

Every git push to the connected branch triggers a new Railway deploy. No CLI commands needed.

Best practice: keep a feature branch, merge to main only when tests pass.

To verify tests pass before pushing:

```
python3 run_all_tests.py
python3 security_audit.py
```

Both should report all-green. If either fails, don't push.

---

## Troubleshooting

### "App crashed" on Railway

Look at the Railway logs. Most common causes:

| Symptom | Likely fix |
|---|---|
| `ModuleNotFoundError` | Missing entry in `requirements.txt` |
| Sessions get cleared on refresh | `FLASK_SECRET_KEY` not set |
| `gunicorn: command not found` | `requirements.txt` doesn't list `gunicorn` |
| 500 errors on every page | Check logs for the actual exception |

### "404 Not Found" on `/static/add_row.js`

Make sure the `static/` folder is committed to git. Empty folders aren't tracked; the `.gitkeep` file inside is what keeps the folder alive.

### Health check failing

Visit `/health` directly. If it returns OK, Railway's health-check config may be wrong (defaults usually work). If it doesn't return OK, the app itself is the problem — check logs.

---

## Security checklist before going live

Run this before considering the deploy "done":

```
python3 security_audit.py
```

Expected output: `AUDIT COMPLETE: 20 passed, 0 failed`.

If any check fails, fix it before deploying. The audit verifies:

- SECRET_KEY is set and long enough
- Cookies are HttpOnly, SameSite=Lax, and Secure in production
- Request size cap is enforced
- CSRF protection actually rejects bad requests
- XSS escaping is active
- Debug mode is OFF
- Engine input caps still in place
