# Windows Setup Guide (trio-office)

Verified working setup for Windows 11 (this fork's primary platform).
Distilled from the claude-office spike verification (2026-07-20).

## Prerequisites

- Python 3.13+ via `uv` (uv downloads the interpreter automatically)
- Node.js 20+ (npm is used automatically when bun is not installed)
- Claude Code CLI

`make` / `tmux` are NOT required on Windows — use the direct commands below.

## Install dependencies

```powershell
cd backend;  uv sync
cd hooks;    uv sync
cd frontend; npm install
```

## Configure

1. Copy `backend/.env.example` to `backend/.env`.
   This keeps AI summaries disabled (`SUMMARY_BACKEND=disabled`) so the backend
   never invokes the `claude` CLI on its own (zero API billing).
2. Hooks are project-scoped in `.claude/settings.json` (committed). They invoke
   the hook via `uv run --project` — no `uv tool install` and no writes to
   `~/.claude/` are needed. Do NOT run `hooks/install.sh` on this fork.

## Start the servers

```powershell
# Terminal 1 — backend on port 8000 (PYTHONUTF8=1 is REQUIRED, see below)
cd backend
$env:PYTHONUTF8 = "1"
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2 — frontend on port 3000
cd frontend
npm run dev
```

Open http://localhost:3000. Health check: http://localhost:8000/health

### Admin actions need the launch token

State-changing UI actions (SIMULATE / RESET / CLEAR DB, focus, clipboard) are
gated behind an auto-generated API key. The backend prints the authorized
launch URL at startup:

```
Open the UI with this URL to authorize destructive actions:
http://localhost:3000/?token=<generated-key>
```

Use that URL (not the bare one) when you need those buttons.

## Why PYTHONUTF8=1 is required on Windows

Two independent failure modes, one root cause (the locale code page, cp932 on
Japanese Windows, is used instead of UTF-8):

1. **Hook stdin corruption (data-level, breaks the UI silently).** Claude Code
   writes hook payloads to stdin as UTF-8. Without UTF-8 mode Python decodes
   them with cp932, and non-ASCII prompt text (e.g. Japanese) turns into lone
   surrogate characters that get stored in the database. WebSocket broadcasts
   of those events then die with `UnicodeEncodeError: surrogates not allowed`,
   and the office view stays empty while the backend keeps answering 200 OK.
   The committed hook commands pass `--env-file hooks/pyutf8env`
   (`PYTHONUTF8=1`) so hook processes always read stdin as UTF-8.
2. **Backend console logging errors (cosmetic).** rich logs emoji, which the
   cp932 console renderer cannot encode. Starting the backend with
   `PYTHONUTF8=1` avoids the recurring `Logging error` tracebacks.

If the office view is empty but the backend logs show `POST /api/v1/events
... 200 OK`, suspect a stale database written before UTF-8 mode was enabled:
stop the backend and delete `backend/visualizer.db`.

## Running Claude Code against this repo

Any Claude Code session started in this repo directory fires the hooks and
appears in the office view. For scripted / child-process sessions, always
strip the API key so the run bills the subscription, not the API:

```bash
env -u ANTHROPIC_API_KEY claude -p --model haiku "..."
```

(With `ANTHROPIC_API_KEY` set, the CLI silently prefers it over your
claude.ai login and every run becomes API-billed.)

## Ports

| Service  | Port | Notes                        |
|----------|------|------------------------------|
| backend  | 8000 | FastAPI + WebSocket + events |
| frontend | 3000 | Next.js dev server           |
