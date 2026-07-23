---
kind: dependency_management
name: Python and Node.js dependency manifests with pinned frontend versions
category: dependency_management
scope:
    - '**'
source_files:
    - pyproject.toml
    - frontend/package.json
    - frontend/.npmrc
    - frontend/package-lock.json
    - dbmr_workplace_agent.egg-info/requires.txt
---

The repository manages dependencies for two independent toolchains — a Python backend and an Angular frontend — each using its native package manager. There is no unified lockfile or vendoring strategy across the two stacks.

**Python (backend)**
- Manifest: `pyproject.toml` declares runtime and dev dependencies using PEP 621 style ranges (`>=0.110`, `>=2.6`, etc.).
- Build system: setuptools via `setuptools.build_meta`; packages discovered under `app*`.
- Optional extras: `[dev]` group pulls in `pytest`, `pytest-asyncio`, `anyio`.
- No `requirements.txt`, `poetry.lock`, `pipenv.lock`, or vendored `vendor/` directory; installers rely on resolver ranges at build/install time.
- The generated `dbmr_workplace_agent.egg-info/requires.txt` mirrors `pyproject.toml` and is a build artifact, not a source-of-truth lockfile.
- No private PyPI registry or `--index-url` / `PIP_INDEX_URL` configuration is present.

**Node.js (frontend)**
- Manifest: `frontend/package.json` pins every dependency to exact versions (e.g. `@angular/core: 21.2.18`, `zod: 4.4.3`).
- Lockfile: `frontend/package-lock.json` is committed alongside the manifest, ensuring reproducible installs.
- Engine constraints: `.npmrc` sets `engine-strict=true` and `save-exact=true`; `package.json` restricts Node to `^20.19.0 || ^22.12.0 || ^24.0.0` and npm `>=10`.
- Audit enabled via `audit=true` in `.npmrc`; `fund=false` suppresses sponsor prompts.
- No private npm registry or `.npmrc` `registry=` override is configured.

**Cross-cutting conventions**
- Backend uses flexible version ranges (resilient to upstream updates); frontend uses exact pinning + lockfile (deterministic builds).
- Dev-only dependencies are isolated into separate groups (`[project.optional-dependencies]` for Python, `devDependencies` for Node) rather than mixed with runtime deps.