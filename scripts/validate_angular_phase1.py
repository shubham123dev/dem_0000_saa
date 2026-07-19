#!/usr/bin/env python3
"""Static, dependency-free validation for the Angular Phase 1 foundation."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

EXPECTED_PACKAGES = {
    "@angular/core": "21.2.18",
    "@angular/common": "21.2.18",
    "@angular/compiler": "21.2.18",
    "@angular/platform-browser": "21.2.18",
    "@angular/router": "21.2.18",
    "@angular/cdk": "21.2.14",
    "zod": "4.4.3",
    "@angular/cli": "21.2.18",
    "@angular/build": "21.2.18",
    "typescript": "5.9.3",
    "vitest": "4.1.10",
    "@playwright/test": "1.61.1",
}

REQUIRED_FILES = (
    "frontend/package.json",
    "frontend/angular.json",
    "frontend/proxy.conf.json",
    "frontend/tsconfig.json",
    "frontend/tsconfig.app.json",
    "frontend/tsconfig.spec.json",
    "frontend/tsconfig.e2e.json",
    "frontend/eslint.config.mjs",
    "frontend/playwright.config.ts",
    "frontend/public/config/app-config.json",
    "frontend/src/main.ts",
    "frontend/src/app/app.config.ts",
    "frontend/src/app/core/config/app-config.model.ts",
    "frontend/src/app/core/api/wire.schemas.ts",
    "frontend/src/app/core/api/workplace-agent-api.service.ts",
    "frontend/src/app/core/api/validated-http.service.ts",
    "frontend/src/app/core/api/api-error.interceptor.ts",
    "frontend/src/app/core/auth/auth-header.interceptor.ts",
    "frontend/src/app/core/errors/error-normalizer.ts",
    "frontend/e2e/foundation.spec.ts",
    "frontend/docs/PHASE_1_ARCHITECTURE.md",
    "frontend/docs/PHASE_1_ACCEPTANCE.md",
)

ROUTE_TOKENS = (
    "/health", "/ready", "/ready/details", "/workplace/capabilities",
    "/overview", "/profile", "/users", "/seats", "/reports", "/access",
    "/audit-log", "/nucleus/account", "/nucleus/license", "/nucleus/approval-status",
    "/nucleus/entitlements", "/resources", "/schema", "/search", "/count",
    "/agent/query", "/agent/actions/propose", "/agent/actions",
    "/cancel", "/rollback-proposal", "/execute", "/reconcile", "/audit-replay",
)


def validate(repo: Path) -> None:
    frontend = repo / "frontend"
    phase0_manifest = frontend / "contracts/api-manifest.json"
    if not phase0_manifest.is_file():
        raise RuntimeError("Phase 0 contract manifest is missing.")
    manifest = json.loads(phase0_manifest.read_text(encoding="utf-8"))
    endpoints = manifest.get("endpoints")
    if not isinstance(endpoints, list) or len(endpoints) != 36:
        raise RuntimeError("Phase 0 must expose exactly 36 endpoint contracts.")

    for relative in REQUIRED_FILES:
        if not (repo / relative).is_file():
            raise RuntimeError(f"Missing Phase 1 file: {relative}")

    package = json.loads((frontend / "package.json").read_text(encoding="utf-8"))
    combined = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
    for name, version in EXPECTED_PACKAGES.items():
        if combined.get(name) != version:
            raise RuntimeError(f"Unexpected package pin for {name}: {combined.get(name)!r}")
    scripts = package.get("scripts", {})
    for name in ("typecheck", "lint", "test", "build", "e2e", "validate:phase1"):
        if name not in scripts:
            raise RuntimeError(f"Missing npm script: {name}")

    angular = json.loads((frontend / "angular.json").read_text(encoding="utf-8"))
    project = angular["projects"]["workplace-agent-ui"]
    if project["architect"]["build"]["builder"] != "@angular/build:application":
        raise RuntimeError("Angular application builder is not configured.")
    build_options = project["architect"]["build"]["options"]
    if build_options.get("index") != "src/index.html":
        raise RuntimeError("Angular index document is not configured.")
    if build_options.get("outputPath") != "dist/workplace-agent-ui":
        raise RuntimeError("Angular output path is not deterministic.")
    if project["architect"]["test"]["builder"] != "@angular/build:unit-test":
        raise RuntimeError("Angular Vitest unit-test builder is not configured.")
    if "--proxy-config proxy.conf.json" not in scripts.get("start", ""):
        raise RuntimeError("Angular development proxy is not configured in npm start.")
    proxy = json.loads((frontend / "proxy.conf.json").read_text(encoding="utf-8"))
    if proxy.get("/api", {}).get("target") != "http://127.0.0.1:8000":
        raise RuntimeError("FastAPI development proxy target is invalid.")
    if proxy.get("/api", {}).get("pathRewrite", {}).get("^/api") != "":
        raise RuntimeError("FastAPI proxy must strip the /api prefix.")

    runtime_config = json.loads((frontend / "public/config/app-config.json").read_text(encoding="utf-8"))
    if runtime_config.get("streamTransport") not in ("rest", "sse"):
        raise RuntimeError("Phase 1 must not claim that streaming exists.")
    if runtime_config.get("apiBaseUrl") != "/api":
        raise RuntimeError("Phase 1 must use the same-origin /api browser boundary.")

    api_text = (frontend / "src/app/core/api/workplace-agent-api.service.ts").read_text(encoding="utf-8")
    for token in ROUTE_TOKENS:
        if token not in api_text:
            raise RuntimeError(f"API facade route token missing: {token}")
    if len(re.findall(r"Observable<", api_text)) < 31:
        raise RuntimeError("API facade does not expose all 31 typed operations.")
    if "approve(id:string" not in api_text or "reject(id:string" not in api_text:
        raise RuntimeError("Approval decision methods are missing.")
    if "agentQueryRequestSchema.parse" not in api_text:
        raise RuntimeError("Agent query requests are not runtime-validated.")
    if "agentActionListFiltersSchema.parse" not in api_text:
        raise RuntimeError("Proposal-list filters are not runtime-validated.")
    shell = (frontend / "src/app/app.component.html").read_text(encoding="utf-8")
    if "apiBaseUrl" in shell or "<dt>API</dt>" in shell:
        raise RuntimeError("The non-technical shell must not expose API infrastructure.")

    all_typescript = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (frontend / "src/app").rglob("*.ts")
        if not path.name.endswith(".spec.ts")
    )
    if re.search(r"(:\s*any\b|<any>)", all_typescript):
        raise RuntimeError("Explicit any is forbidden in Phase 1 source.")
    if "new EventSource" in all_typescript or "new WebSocket" in all_typescript:
        raise RuntimeError("Phase 1 must not invent a streaming transport.")

    boundary = subprocess.run(
        ["node", "scripts/check-architecture-boundaries.mjs"],
        cwd=frontend,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if boundary.returncode != 0:
        raise RuntimeError(boundary.stdout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    validate(repo)
    print("Angular Phase 1 foundation is valid: 31 typed API operations, strict runtime boundaries, and no fake streaming.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
