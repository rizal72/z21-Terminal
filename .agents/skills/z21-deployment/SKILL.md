---
name: z21-deployment
description: PROACTIVE USE REQUIRED - Contains ALL critical rules for z21-Terminal project. MUST be followed for EVERY git operation (commit/push), deployment, Python command, and development task. Auto-apply without user prompting. Includes git workflow, venv activation, deployment decision tree, encoding rules, PowerShell aliases, and all non-negotiable project rules. Use proactively whenever working on z21-Terminal.
---

# z21-Terminal Deployment Workflow

**CRITICAL**: ALWAYS use PowerShell aliases. NEVER execute git/npm commands manually.

---

## Complete Workflow (Mac -> PC)

**EVERY TIME you complete a feature/fix**:

1. **Mac Development**: Write code, test locally (optional)
2. **Mac Commit**: `git add . && git commit -m "message"`
3. **Mac Push**: `git push`
4. **PC Deploy**: `ssh riccardo@gaming-pc "cd C:\z21-Terminal && z21-deploy-dev"`
5. **PC Test**: Open browser, verify changes work in production environment

**CRITICAL**: Steps 1-3 are NOT enough! MUST deploy to PC (step 4) to test properly.

**Why**: Mac is development only, PC is production environment with GPU, Task Scheduler, real Z21 hardware.

---

## Deployment Decision Tree

**Check what changed, then apply**:

**Docs only** (`AGENTS.md`, `README.md`, `docs/*`):
```bash
ssh riccardo@gaming-pc "cd C:\z21-Terminal && git pull"
```

**Backend only** (`backend/*`):
```bash
ssh riccardo@gaming-pc "cd C:\z21-Terminal && git pull && z21-restart"
```

**Frontend only** (`web/src/*` or `web/index.html`):
```bash
ssh riccardo@gaming-pc "cd C:\z21-Terminal && z21-deploy-dev"
```

**Both Frontend + Backend**:
```bash
ssh riccardo@gaming-pc "cd C:\z21-Terminal && z21-deploy-dev"
```

---

## PowerShell Aliases (PC Windows)

### Deployment Aliases

**z21-deploy-dev** (Development deploy from `develop` branch):
```bash
ssh riccardo@gaming-pc "cd C:\z21-Terminal && z21-deploy-dev"
```
- Switch to `develop` branch
- `git reset --hard origin/develop` (preserves config.local.json)
- `npm install` + `npm run build`
- `z21-restart`

**z21-deploy** (Production deploy from `main` branch):
```bash
ssh riccardo@gaming-pc "cd C:\z21-Terminal && z21-deploy"
```
- Same as z21-deploy-dev but on `main` branch

### Backend Management Aliases

**z21-start** (Start backend - idempotent, FIRST launch):
```bash
ssh riccardo@gaming-pc "cd C:\z21-Terminal && z21-start"
```
- Checks if the Task Scheduler task is already Running; starts only if not
- Use for the FIRST launch of a session (e.g. after `wol` remote wake-up)
- `z21-restart` = full stop + start cycle (use ONLY when backend is already running)

**z21-restart** (Restart backend):
```bash
ssh riccardo@gaming-pc "cd C:\z21-Terminal && z21-restart"
```
- Stop backend via Task Scheduler
- Kill stray Python processes
- Start backend via Task Scheduler (survives SSH close)

**z21-stop** (Stop backend):
```bash
ssh riccardo@gaming-pc "cd C:\z21-Terminal && z21-stop"
```
- Stop backend Task Scheduler task
- Kill Python processes
- Log file: `C:\z21-Terminal\backend.log`

**z21-log** (View backend logs):
```bash
ssh riccardo@gaming-pc "cd C:\z21-Terminal && z21-log"
```
- Shows `backend.log` content (equivalent to `tail -f`)
- Use when debugging deployment issues or backend errors

### Development Aliases (Mac only)

**z21** - Launch backend + frontend in iTerm2 tabs
**z21-backend** - Backend FastAPI only (port 8000)
**z21-frontend** - Frontend Vite only (port 5173)
**z21-terminal** - CLI controller (z21_controller.py)

---

## Database Debugging (PC -> Mac)

**ALWAYS copy database from PC to Mac before running SQL queries**

**Why**: PowerShell SSH sessions make complex SQL queries difficult (escaping issues, syntax errors)

**Pattern**:
```bash
# Copy database from PC to Mac (overwrites backend/data/data.db)
scp riccardo@gaming-pc:C:/z21-Terminal/backend/data/data.db backend/data/data.db

# Now run queries locally on Mac
sqlite3 backend/data/data.db "SELECT ..."
```

**Benefits**:
- No escaping issues (native SQLite on Mac)
- Mac DB stays up-to-date with PC production data
- Faster query development (local REPL)
- `backend/data/data.db` is gitignored (won't be committed)

**When to use**: Any time you need to run SQL queries for debugging, testing, or analysis

**Example workflow**:
```bash
# 1. Copy fresh DB from PC
scp riccardo@gaming-pc:C:/z21-Terminal/backend/data/data.db backend/data/data.db

# 2. Run queries locally
sqlite3 backend/data/data.db "
  SELECT COUNT(*) FROM events
  WHERE event_type='delta_t'
    AND json_extract(data, '\$.consist_id')=11
"

# 3. No need to commit (DB is gitignored)
```

---

## CRITICAL Rules (NON-NEGOTIABLE)

### 1. Python Virtual Environment

**Mac Development**:
```bash
# ALWAYS activate venv before running Python commands
source venv/bin/activate
python -m py_compile backend/main.py
```

**PC Production**:
- venv gestito automaticamente da Task Scheduler (`z21-restart`)
- Per comandi manuali: `.\venv\Scripts\Activate.ps1`

**Why**: PyTorch, ultralytics, FastAPI installed in venv, NOT system-wide. Without venv = ModuleNotFoundError.

---

### 2. Git Workflow

**ALWAYS use `git add .`** (NOT single files):
```bash
git add .                    # CORRECT
git commit -m "message"
git push
```

**NEVER**:
```bash
git add file1.py file2.jsx   # WRONG - use git add .
```

**Why**: Secret files (.env, config.local.json) and private agent notes (AGENTS.md, CLAUDE.md) are gitignored. Legacy agent tool dirs (`.claude/`, `.opencode/`, `.pi/`) are also gitignored; the consolidated `.agents/` dir (project skills) IS tracked.

**Branch Strategy**:
- Daily work: `develop` branch
- Releases: `main` branch
- CRITICAL: Always return to `develop` after merging to main

**Fast-forward merge ONLY**:
```bash
git checkout main
git merge develop --ff-only   # CORRECT (no merge commits)
git checkout develop          # NEVER forget this!
```

---

### 3. Frontend Changes Require Rebuild

**Backend changes** (`backend/*`):
- Python is interpreted -> `z21-restart` is enough

**Frontend changes** (`web/src/*`):
- Static build required -> `z21-deploy-dev` (rebuild)
- NEVER just `z21-restart` for frontend changes!

**Why**: Frontend = built static files in `web/dist/`. Restart backend does NOT rebuild frontend.

---

### 4. NEVER Commit Secret/Private Files

**NEVER commit** (gitignored):
- `.env` files (secrets, API keys)
- agent tool directories (`.claude/`, `.opencode/`, `.pi/` - legacy)
- `config.local.json` (local overrides)
- `config.local.py` (local Python config)
- `secrets.json`, `camera_config.json`
- Any file with passwords, tokens, or credentials

**OK to commit** (project documentation):
- `docs/*.md` (documentation)
- `README.md` (GitHub readme)
- `.agents/` (project agent skills, e.g. this skill)

**Check before commit**:
```bash
git status
# Ensure no .env, .claude/, or secret files staged
```

---

### 5. Git Remote: SSH Only

**ALWAYS use SSH** (NOT HTTPS):
```bash
git remote -v
# Should show: git@github.com:rizal72/z21-Terminal.git (CORRECT)
# NOT: https://github.com/rizal72/z21-Terminal.git (WRONG)
```

**If HTTPS**: Fix with:
```bash
git remote set-url origin git@github.com:rizal72/z21-Terminal.git
```

**Why**: SSH = secure, automatic auth. HTTPS = token management headache.

---

### 6. Encoding Rules

**NEVER use non-ASCII in code/logs**:
```python
# WRONG
print("[emoji] Success")
print("Delta-t calculation")
console.log("Locomotive detected")
```

Wait - WRONG example is the non-ASCII one. Correct pattern:

```python
# WRONG: non-ASCII in backend code/logs (unicode arrows, greek letters, emoji)
# CORRECT:
print("[SUCCESS]")
print("Delta-t calculation")
console.log("Locomotive detected")
```

**Emoji OK ONLY in UI** (frontend JSX/HTML, NOT backend logs).

**Why**: Windows console (Task Scheduler) displays garbled output with emoji/unicode.

---

### 7. README Language

**README.md**: ALWAYS English (GitHub community)
**AGENTS.md**: Can be Italian (private agent notes, untracked)

---

## Config Files Behavior

**config.json** (tracked in git):
- Overwritten by `git reset --hard` (deploy aliases)
- Contains default configuration

**config.local.json** (gitignored):
- NEVER overwritten by deploy
- Use for local overrides (camera settings, test mode)

Deploy preserves local overrides:
```
z21-deploy-dev -> git reset --hard -> config.json overwritten
             -> config.local.json PRESERVED
```

---

## PC Info

- **SSH**: `riccardo@gaming-pc`
- **Path**: `C:\z21-Terminal`
- **Shell**: PowerShell 7.5.4
- **Log file**: `C:\z21-Terminal\backend.log`

---

## Pre-Deploy Checklist (What the AI Agent Must Verify)

Before ANY deployment, the AI agent MUST check:

1. **Venv activated?** (Mac only - `source venv/bin/activate`)
2. **Git status clean?** (no .env or secret files staged)
3. **Correct branch?** (`develop` for daily work, `main` for releases)
4. **What changed?** (frontend/backend/docs -> correct command)
5. **Username included?** (`riccardo@gaming-pc`, NOT just `gaming-pc`)
6. **Using alias?** (z21-deploy-dev, NOT manual git/npm)

---

## What the AI Agent Should Do

When user says "deploy to PC", "push to production", "update PC", "check logs":

**Step 1**: Check what changed (frontend/backend/docs)
**Step 2**: Verify pre-deploy checklist (above)
**Step 3**: Use correct alias with username
**Step 4**: NEVER execute manual git/npm commands

**Example**:
```
User: "Ho modificato SpeedTableViewer.jsx, puoi deployare?"

The agent checks:
- Frontend modified (web/src/*) -> z21-deploy-dev
- Username: riccardo@gaming-pc

Execute:
ssh riccardo@gaming-pc "cd C:\z21-Terminal && z21-deploy-dev"
```

---

## CHANGELOG Management Policy

**Structure**: `docs/CHANGELOG.md` (active, last ~30 days) -> `docs/CHANGELOG_ARCHIVE.md` (history).

**Strategy**:
1. **Recent Changes (Last 30 Days)**: only in `docs/CHANGELOG.md`
   - Concise entries: date + section (Feature/Bug fix/Docs), commits referenced
   - Technical details -> link to `docs/*.md` (don't duplicate)
   - AGENTS.md stays slim and AI-readable: rules and pointers only, NO changelog entries

2. **Technical Details**: always in dedicated docs
   - Architecture -> docs/REFACTOR_PLAN.md, FRONTEND_REFACTOR_PLAN.md
   - Features -> docs/FEATURE_NAME.md (26+ specialized docs exist)

3. **When to Archive**:
   - Quarterly (every 3 months)
   - Move old entries from `docs/CHANGELOG.md` to the TOP of `docs/CHANGELOG_ARCHIVE.md` (reverse chronological)
   - Commit: "docs: archive changelog (pre-YYYY-MM-DD)"

**Why**: Keep `docs/CHANGELOG.md` focused on current work; AGENTS.md lean; history preserved in CHANGELOG_ARCHIVE.md.

---

## Summary

**This skill contains ALL critical rules for z21-Terminal deployment. The AI agent MUST follow every rule without exception.**

Key Points:
- 7 CRITICAL rules (venv, git workflow, frontend rebuild, secrets, SSH protocol, encoding, README language)
- Deployment decision tree (docs/backend/frontend)
- PowerShell aliases (z21-start, z21-deploy-dev, z21-deploy, z21-restart, z21-stop, z21-log)
- Pre-deploy checklist (6 items)
- Config files behavior (config.json vs config.local.json)
- Database debugging pattern (PC -> Mac copy workflow)
- CHANGELOG management policy (active docs/CHANGELOG.md, quarterly archive)

**All commands include `ssh riccardo@gaming-pc` and use aliases. Zero duplications.**
