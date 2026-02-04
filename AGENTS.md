# AGENTS.md - Development Guidelines for Agentic Coding Assistants

## Build, Lint, and Test Commands

### Frontend (React + Vite)
```bash
cd web
npm run dev      # Start dev server (port 5173) with HMR
npm run build    # Production build (outputs to web/dist/)
npm run lint     # Run ESLint on all .js/.jsx files
npm run preview  # Preview production build
```

### Backend (Python + FastAPI)
```bash
pyright backend/                    # Run Pyright type checker
pyright backend/main.py             # Check specific file
source venv/bin/activate && python backend/main.py  # Start backend (Mac)
```

### Testing (Memory Testing - No Traditional Unit Tests)
```bash
./test/memory/run_full_memory_test.sh                    # Full memory test suite
./test/memory/run_full_memory_test.sh --duration 5       # 5-minute test
./test/memory/run_full_memory_test.sh --backend-only     # Backend only
./test/memory/run_full_memory_test.sh --frontend-only    # Frontend only
python3 test/memory/backend_memory_monitor.py --interval 5 --duration 10  # Direct backend monitoring
```

**Note**: No pytest/jest/vitest tests exist. Testing focuses on memory monitoring and Docker deployment validation.

---

## Mac Development Aliases (zsh + iTerm2)

Located in: `~/.bash_aliases`

```bash
z21              # Start backend + frontend in separate iTerm2 tabs
z21-backend      # Backend only (port 8000)
z21-frontend     # Frontend only (port 5173)
z21-terminal     # CLI locomotive controller
```

**Usage**: Run from project root. Aliases automatically handle venv activation.

---

## PC Production Deployment Aliases (PowerShell 7.5.4)

Located in: `C:\Users\Riccardo\Documents\PowerShell\Microsoft.PowerShell_profile.ps1`

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

**z21-log** (View backend logs):
```bash
ssh riccardo@gaming-pc "cd C:\z21-Terminal && z21-log"
```
- Shows `backend.log` content (equivalent to `tail -f`)
- Use when debugging deployment issues or backend errors

---

## Complete Workflow (Mac → PC)

**EVERY TIME you complete a feature/fix**:

1. **Mac Development**: Write code, test locally (optional)
2. **Mac Commit**: `git add . && git commit -m "message"`
3. **Mac Push**: `git push`
4. **🚨 PC Deploy**: `ssh riccardo@gaming-pc "cd C:\z21-Terminal && z21-deploy-dev"`
5. **PC Test**: Open browser, verify changes work in production environment

**⚠️ CRITICAL**: Steps 1-3 are NOT enough! MUST deploy to PC (step 4) to test properly.

**Why**: Mac is development only, PC is production environment with GPU, Task Scheduler, real Z21 hardware.

---

## Deployment Decision Tree

**Check what changed, then apply**:

**Docs only** (`CLAUDE.md`, `README.md`, `docs/*`):
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

## Code Style Guidelines

### Python (Backend)

**Imports**: Standard library first, third-party next, local modules last
```python
from pathlib import Path
import sqlite3
from fastapi import APIRouter, Depends
from services.data_db import DataDB
```

**Type Hints**: Required for all public functions
```python
def get_validated_sessions(limit: Optional[int] = None) -> List[Dict]:
    """Get validated sessions from database."""
```

**Naming**: snake_case for functions/variables, PascalCase for classes
```python
class DataDB:
    def get_latest_session(self) -> Optional[Dict]:
        pass
```

**Docstrings**: Google-style docstrings for all public functions/classes
```python
async def poll_track_power():
    """Background task to monitor Z21 track power state."""
```

**Error Handling**: Try/except with logging, never bare except
```python
try:
    status = z21_manager.z21.get_status()
except Exception as e:
    log('[ERROR]', f'Failed to get Z21 status: {e}')
    return None
```

**CRITICAL**: No emoji in backend code/logs. Use ASCII-only characters in all log messages.
```python
# ❌ WRONG
print("✅ Success")
print("Δt calculation")

# ✅ CORRECT
print("[SUCCESS]")
print("Delta-t calculation")
```

**Database Access**: Use DataDB service class, never import sqlite3 directly in endpoints
```python
from services.data_db import DataDB
session = DataDB.get_latest_session()
```

**Async/Await**: All FastAPI endpoints must be async
```python
@router.get("/api/status")
async def api_status():
    return {"status": "running"}
```

### React (Frontend)

**Imports**: React hooks first, third-party next, local modules last
```javascript
import { useState, useEffect } from 'react';
import Recharts from 'recharts';
import { formatDeltaT } from '../utils/analyticsHelpers';
```

**Components**: Functional components only, no class components
```javascript
export default function ConsistController({ consist, onSpeedChange }) {
  const [speed, setSpeed] = useState(0);
  return <div>...</div>;
}
```

**Naming**: camelCase for variables/functions, PascalCase for components
```javascript
const handleSave = async () => { ... }
export default function SettingsModal() { ... }
```

**JSDoc Comments**: For all exported functions
```javascript
/**
 * Filter events by session (Current vs Overview mode)
 */
export const filterEventsBySession = (events, viewMode, currentSession) => {
  return viewMode === 'current' ? events.filter(...) : events;
};
```

**Error Handling**: Try/catch with console.error
```javascript
try {
  const response = await fetch(url);
  const data = await response.json();
} catch (err) {
  console.error('Settings load error:', err);
  setError(err.message);
}
```

**Styling**: Tailwind CSS utility classes only, no custom CSS files
```javascript
<div className="bg-control-black text-white p-4 rounded">
  <button className="bg-signal-red hover:bg-red-700 text-white px-4 py-2">
    Save
  </button>
</div>
```

**Emoji**: Allowed in UI components (frontend JSX), NEVER in backend code/logs

---

## Project-Specific Rules

### Virtual Environment

**Mac Development**:
```bash
# ALWAYS activate venv before running Python commands
source venv/bin/activate
python -m py_compile backend/main.py
```

**PC Production**:
- venv managed automatically by Task Scheduler (`z21-restart`)
- For manual commands: `.\venv\Scripts\Activate.ps1`

**Why**: PyTorch, ultralytics, FastAPI installed in venv, NOT system-wide.

### Git Workflow

**ALWAYS use `git add .`** (NOT single files):
```bash
git add .                    # ✅ CORRECT
git commit -m "message"
git push
```

**Branch Strategy**:
- Daily work: `develop` branch
- Releases: `main` branch
- ⚠️ CRITICAL: Always return to `develop` after merging to main

**Fast-forward merge ONLY**:
```bash
git checkout main
git merge develop --ff-only   # ✅ CORRECT (no merge commits)
git checkout develop          # ⚠️ NEVER forget this!
```

### Frontend Changes Require Rebuild

**Backend changes** (`backend/*`):
- Python is interpreted → `z21-restart` is enough ✅

**Frontend changes** (`web/src/*`):
- Static build required → `z21-deploy-dev` (rebuild) ✅
- ❌ NEVER just `z21-restart` for frontend changes!

**Why**: Frontend = built static files in `web/dist/`. Restart backend does NOT rebuild frontend.

### Config Files Behavior

**config.json** (tracked in git):
- Overwritten by `git reset --hard` (deploy aliases)
- Contains default configuration

**config.local.json** (gitignored):
- NEVER overwritten by deploy
- Use for local overrides (camera settings, test mode)

Deploy preserves local overrides:
```
z21-deploy-dev → git reset --hard → config.json overwritten
             → config.local.json PRESERVED
```

### Database Debugging Pattern

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
- ✅ No escaping issues (native SQLite on Mac)
- ✅ Mac DB stays up-to-date with PC production data
- ✅ Faster query development (local REPL)
- ✅ `backend/data/data.db` is gitignored (won't be committed)

### Backend Architecture

**Modular v1.0.0** - Use existing routers and services. Don't modify `main.py` unless necessary.

- **Routers** (API endpoints): analytics, config, roster, status, speed_table
- **Services** (business logic): broadcast, config_manager, data_db
- **WebSocket Handlers**: ws_control, ws_tracking

### Type Checking

Run `pyright backend/` before committing major backend refactoring. Current baseline: 26 errors (intentionally deferred, see docs/PYRIGHT_ANALYSIS.md).

### Hot Reload

- **Frontend**: Automatic (Vite HMR)
- **Backend**: Manual restart required for Python changes

---

## Pre-Deploy Checklist (What Claude Must Verify)

Before ANY deployment, Claude MUST check:

1. ✅ **Venv activated?** (Mac only - `source venv/bin/activate`)
2. ✅ **Git status clean?** (no .env or secret files staged)
3. ✅ **Correct branch?** (`develop` for daily work, `main` for releases)
4. ✅ **What changed?** (frontend/backend/docs → correct command)
5. ✅ **Username included?** (`riccardo@gaming-pc`, NOT just `gaming-pc`)
6. ✅ **Using alias?** (z21-deploy-dev, NOT manual git/npm)

---

## PC Info

- **SSH**: `riccardo@gaming-pc`
- **Path**: `C:\z21-Terminal`
- **Shell**: PowerShell 7.5.4
- **Log file**: `C:\z21-Terminal\backend.log`

---

## What Claude Should Do

When user says "deploy to PC", "push to production", "update PC", "check logs":

**Step 1**: Check what changed (frontend/backend/docs)
**Step 2**: Verify pre-deploy checklist (above)
**Step 3**: Use correct alias with username
**Step 4**: NEVER execute manual git/npm commands

**Example**:
```
User: "Ho modificato SpeedTableViewer.jsx, puoi deployare?"

Claude checks:
- Frontend modified (web/src/*) → z21-deploy-dev ✅
- Username: riccardo@gaming-pc ✅

Execute:
ssh riccardo@gaming-pc "cd C:\z21-Terminal && z21-deploy-dev"
```

---

## Access URLs

- **Mac Dev**: http://localhost:5173 or http://192.168.1.xxx:5173
- **Mac Dev (Tailscale)**: https://mbp16diriccardo.tail9350d7.ts.net
- **PC Prod Local**: http://localhost:8000
- **PC Prod (Tailscale)**: https://gaming-pc.tail9350d7.ts.net

---

## Documentation

For more detailed information, see:
- `CLAUDE.md` - Main project documentation (Italian)
- `README.md` - Project overview and usage (English)
- `docs/PYRIGHT_ANALYSIS.md` - Type checking guidelines
- `.claude/skills/z21-deployment/SKILL.md` - Complete deployment workflow and critical rules (393 lines)
- 26+ specialized documentation files in `docs/`
