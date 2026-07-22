# Angular frontend contract workspace

Phase 0 intentionally contains contracts and validation only. The Angular application is created after these interfaces are accepted.

- `docs/BACKEND_API_CONTRACT.md`: exact current FastAPI surface.
- `docs/AGENT_EVENT_CONTRACT.md`: planned safe Angular event envelope.
- `docs/ERROR_CONTRACT.md`: current error wire format and future UI normalization.
- `docs/PHASE_0_GAPS.md`: interfaces that do not exist yet.
- `contracts/api-manifest.json`: machine-readable route inventory.
- `contracts/ui-event.schema.json`: planned normalized UI-event schema.
- `contracts/examples/`: valid example payloads.

Validate from repository root:

```bash
python scripts/validate_frontend_contracts.py --repo .
pytest -q tests/test_frontend_contracts.py
```

<!-- ANGULAR_FRONTEND_PHASE_1_FOUNDATION -->
## Phase 1 Angular foundation

The repository now contains a strict Angular 21 LTS application, a runtime
configuration bootstrap, functional request/auth/error interceptors, Zod
validation for the current backend wire contracts, and a single typed facade
covering all 31 Phase 0 endpoint method/path pairs.

```bash
cd frontend
npm install
npm run validate:phase1
npx playwright install chromium
npm run e2e
```

The current shell is intentionally structural. Cloudflare-style visual tokens
and reusable controls are implemented in Phase 2; full dashboard and Ask AI
experiences follow in later phases.


### Local API routing

The browser uses the same-origin `/api` prefix. `npm start` loads
`proxy.conf.json`, forwards `/api/*` to the local FastAPI server at
`http://127.0.0.1:8043`, and removes the prefix. Production must provide the
same reverse-proxy contract. This avoids exposing endpoint infrastructure in the
non-technical UI and avoids cross-origin custom-header failures.

<!-- ANGULAR_FRONTEND_PHASE_2_DESIGN_SYSTEM -->
## Phase 2 design system

The Angular frontend now has semantic light/dark themes, ten accessible UI primitives, a visual showcase, and automated token/component validation. See `frontend/docs/DESIGN_SYSTEM.md`.

<!-- ANGULAR_FRONTEND_PHASE_3_SHELL -->
## Phase 3 workplace shell

The Angular app now uses the production-shaped three-panel workplace shell. Phase 2 hardening adds contrast validation, pre-bootstrap theming, ControlValueAccessor form controls, and native action surfaces.

<!-- ANGULAR_FRONTEND_PHASE_4_CONVERSATION -->
## Phase 4 Ask AI conversation

The responsive Ask AI panel is connected to `WorkplaceAgentApiService.query`. It renders all three current backend response modes, keeps only normalized current-tab history, and never invents streaming or hidden reasoning.
<!-- ANGULAR_FRONTEND_PHASE_5_DURABLE_RUNS -->
## Phase 5 durable runs and live activity

Ask AI now uses backend-authoritative conversations and resumable authenticated SSE. The browser keeps only recovery identifiers and a replay cursor; `/agent/query` remains the explicit REST fallback.

<!-- PHASE_6_GOVERNED_ACTION_CONTROL_PLANE -->
## Phase 6 Approval Center

Pending approvals now open a responsive governed control plane backed by real proposal projections, backend-derived operations, explicit execution, resumable execution SSE, safe receipts, reconciliation, and governed rollback proposals.

---

## 📦 Build Output (`dist/`) & Deployment Guide (For Beginners)

### 1. Is `dist/` in `.gitignore`?
**Yes.** Verified in [frontend/.gitignore](file:///c:/Users/Shubham%20Shrivastav/Desktop/openai/open_ai_worked_workspace_chat/frontend/.gitignore#L2).
- The `dist/` directory is **excluded from Git** so generated build files do not clutter source control repositories.

---

### 2. What is the `dist/` folder?
The `dist/` (Distribution) folder contains the final, compiled HTML, CSS, and bundled JavaScript files. 
- Browsers cannot run TypeScript (`.ts`) natively. `ng build` translates your source code into optimized JavaScript files inside `dist/`.

---

### 3. When should you run `ng build` (update `dist/`)?

| Scenario | Command to run | Why? |
| :--- | :--- | :--- |
| **Local Development** | `npm run dev` (or `npx ng serve`) | You **do NOT need `dist/`** for daily development. The dev server compiles code in memory with live hot-reloading. |
| **Testing Production Build** | `npx ng build --configuration=development` | Generates a fresh `dist/` output for local manual verification or integration testing. |
| **Deploying to Web Server / Staging** | `npx ng build --configuration=production` | Generates a minified, production-optimized `dist/` folder ready to be hosted on Nginx, Apache, S3, Vercel, or Netlify. |

---

### 4. Step-by-Step Command Cheat Sheet

```bash
# Move into frontend folder
cd frontend

# Run local dev server (Frontend runs on http://127.0.0.1:4201 with backend proxy to http://127.0.0.1:8043)
npm start
# OR: npx ng serve --host 127.0.0.1 --port 4201 --proxy-config proxy.conf.json

# Run unit tests
npx ng test --watch=false

# Rebuild dist folder for testing
npx ng build --configuration=development

# Build optimized dist for production deployment
npx ng build --configuration=production
```

---

### 5. 🐧 Deploying to an Ubuntu Server

#### Port Matching Reference
- **Frontend Port**: `4201` (Dev mode) / `80` (Nginx HTTP)
- **Backend API Port**: `8043` (FastAPI backend target in `proxy.conf.json`)

#### Option A: Build locally and copy `dist/` to Ubuntu Nginx (Recommended)
```bash
# 1. Build production dist on your machine
npx ng build --configuration=production

# 2. Copy dist files to your Ubuntu server (from Windows PowerShell / local terminal)
scp -r dist/workplace-agent-ui/browser/* username@your-ubuntu-ip:/var/www/html/
```
On Ubuntu, restart Nginx:
```bash
sudo systemctl restart nginx
```

#### Option B: Build and run directly on Ubuntu
```bash
# 1. Clone repository & enter frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Build for production
npx ng build --configuration=production

# 4. Serve statically or run dev server on matching port 4201
npx serve -s dist/workplace-agent-ui/browser -l 4201
# OR dev mode accessible on remote network:
npx ng serve --host 0.0.0.0 --port 4201 --proxy-config proxy.conf.json
```

