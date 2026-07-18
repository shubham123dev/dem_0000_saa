#!/usr/bin/env python3
"""Apply the complete Angular frontend Phase 1 foundation and API client."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

EXPECTED_BRANCH = "main"
EXPECTED_BASE = "1863fc0ec62b148dc1976c154afa1f91e3375c16"
EXPECTED_REPOSITORY = "shubham123dev/dem_0000_saa"

NPM = "npm.cmd" if sys.platform == "win32" else "npm"
PHASE0_MARKER = "ANGULAR_FRONTEND_PHASE_0_CONTRACTS"
PHASE1_MARKER = "ANGULAR_FRONTEND_PHASE_1_FOUNDATION"

PHASE0_HASHES = {'frontend/README.md': 'c184f511e01c465251ce9716a26403b103909eb765b5ae9417b6e4f01648cec4',
 'frontend/contracts/README.md': '5bcd260c2820d0acf2779df8895497f51d927738cb76e049253b45dd55a0b283',
 'frontend/contracts/api-manifest.json': '27555478120d8cd78ed9ef592b1a42afcdc4772da39b1cf76861a529f12f0a7b',
 'frontend/contracts/examples/agent-action-proposal.json': '944f9d588541ae3171aa4de99e8ccc4e338e23914feba7a985b3d0e21f095e6e',
 'frontend/contracts/examples/agent-clarification.json': '27fb9e2cbfd4365ae14c3ed40090fd140e1b1df54f8c2c8d5a3cb27aa3859820',
 'frontend/contracts/examples/agent-read-answer.json': 'c3a12a82ef45c1e63c9a70892d7a7d4feb0d5057f6691686e422e74e28a1f06a',
 'frontend/contracts/examples/approval-approved.json': '5166ebb6840692c6a8b9bcb833d3734684a400f1eb81b5014fb18db0702b3e4c',
 'frontend/contracts/examples/capabilities-shape.json': 'e989e36f596859333b373706624134429e8f889bfd7e604cb4b6d8d88b94e230',
 'frontend/contracts/examples/error-stale.json': '5d97f93c220ab28653951ed59422042683304bd63f8dbd4c2a7d233d7bac258b',
 'frontend/contracts/examples/execution-reconciliation-required.json': 'a0d7138b7c4736dea4d77ddbec30721781e49f221203aaccd2eb55c22c5b35a8',
 'frontend/contracts/examples/execution-succeeded.json': 'd28dcb9c65d043f2a1430c8e083678a4eaf1cd77504165b8e11dfaebbb5e6887',
 'frontend/contracts/examples/proposal-pending.json': '685bc66e87a2fa8b617c30c7a007f87000d13d2dc550534909ec1b9af95f9d04',
 'frontend/contracts/examples/resource-search.json': 'c8d4494b6b3bf2211c5a1aab128d70bb540669cdf0fce2c0c3127662b36820eb',
 'frontend/contracts/examples/ui-activity-update.json': '7c1bc910aeb91e5c47809c03becd2504ab5d9b6c185c42238e07c32fb536c9c7',
 'frontend/contracts/examples/ui-execution-update.json': '9f63668b70e1d01ec7724ca5fcca7c9c00224729a91bf7b6cdeff6097aeca83d',
 'frontend/contracts/examples/ui-proposal.json': '7d4aee286c48d6fa4b159a51152a9be32b5721423e8e3daa92344e1c4dd5dba5',
 'frontend/contracts/ui-event.schema.json': 'be843beebd1709d3472630fc4ca9aba319caf1690388865f8ed32ebac60e5b00',
 'frontend/docs/AGENT_EVENT_CONTRACT.md': '1bf0d04b27a2ca3f98dc294300672109b09d7e60dd9047a2107204c3c9b114d3',
 'frontend/docs/BACKEND_API_CONTRACT.md': '52a0b367a60dc348b92553ed7391e8a0320a2650f7f0af8a8b46f412f360f233',
 'frontend/docs/ERROR_CONTRACT.md': 'f8f9fd233c58229342e1cc293b939a71290f95b3c355048c9fede9c2c47350b4',
 'frontend/docs/PHASE_0_ACCEPTANCE.md': '6b1327970bc90fed9e93bcf05ab0955989f25639b15ee1b0ca824b2356f3bf9e',
 'frontend/docs/PHASE_0_GAPS.md': '7e9d9598770e060f7c3c7c76f6ec1577890e47cd397b86de7684ca865471dc2b',
 'scripts/validate_frontend_contracts.py': '122baa56d08ab30a0c593451f5126d618e7ee9bdd8fe397542f535780904532f',
 'tests/test_frontend_contracts.py': 'ac33ec3f2a2f61570f38339ca7f715534bb2305bdec378fab00e4d7c711e1db3'}

FILES = {'frontend/.editorconfig': 'root = true\n'
                           '\n'
                           '[*]\n'
                           'charset = utf-8\n'
                           'end_of_line = lf\n'
                           'insert_final_newline = true\n'
                           'indent_style = space\n'
                           'indent_size = 2\n'
                           'trim_trailing_whitespace = true\n'
                           '\n'
                           '[*.md]\n'
                           'trim_trailing_whitespace = false\n',
 'frontend/.gitignore': '/node_modules\n'
                        '/dist\n'
                        '/.angular\n'
                        '/coverage\n'
                        '/playwright-report\n'
                        '/test-results\n'
                        '*.log\n'
                        '.DS_Store\n',
 'frontend/.npmrc': 'audit=true\nfund=false\nsave-exact=true\nengine-strict=true\n',
 'frontend/angular.json': '{\n'
                          '  "$schema": "./node_modules/@angular/cli/lib/config/schema.json",\n'
                          '  "version": 1,\n'
                          '  "newProjectRoot": "projects",\n'
                          '  "projects": {\n'
                          '    "workplace-agent-ui": {\n'
                          '      "projectType": "application",\n'
                          '      "root": "",\n'
                          '      "sourceRoot": "src",\n'
                          '      "prefix": "app",\n'
                          '      "schematics": {\n'
                          '        "@schematics/angular:component": {\n'
                          '          "style": "scss",\n'
                          '          "changeDetection": "OnPush",\n'
                          '          "skipTests": false\n'
                          '        }\n'
                          '      },\n'
                          '      "architect": {\n'
                          '        "build": {\n'
                          '          "builder": "@angular/build:application",\n'
                          '          "options": {\n'
                          '            "browser": "src/main.ts",\n'
                          '            "tsConfig": "tsconfig.app.json",\n'
                          '            "inlineStyleLanguage": "scss",\n'
                          '            "assets": [\n'
                          '              {\n'
                          '                "glob": "**/*",\n'
                          '                "input": "public"\n'
                          '              }\n'
                          '            ],\n'
                          '            "styles": [\n'
                          '              "src/styles.scss"\n'
                          '            ]\n'
                          '          },\n'
                          '          "configurations": {\n'
                          '            "production": {\n'
                          '              "budgets": [\n'
                          '                {\n'
                          '                  "type": "initial",\n'
                          '                  "maximumWarning": "600kB",\n'
                          '                  "maximumError": "900kB"\n'
                          '                },\n'
                          '                {\n'
                          '                  "type": "anyComponentStyle",\n'
                          '                  "maximumWarning": "8kB",\n'
                          '                  "maximumError": "12kB"\n'
                          '                }\n'
                          '              ],\n'
                          '              "outputHashing": "all"\n'
                          '            },\n'
                          '            "development": {\n'
                          '              "optimization": false,\n'
                          '              "extractLicenses": false,\n'
                          '              "sourceMap": true\n'
                          '            }\n'
                          '          },\n'
                          '          "defaultConfiguration": "production"\n'
                          '        },\n'
                          '        "serve": {\n'
                          '          "builder": "@angular/build:dev-server",\n'
                          '          "configurations": {\n'
                          '            "production": {\n'
                          '              "buildTarget": "workplace-agent-ui:build:production"\n'
                          '            },\n'
                          '            "development": {\n'
                          '              "buildTarget": "workplace-agent-ui:build:development"\n'
                          '            }\n'
                          '          },\n'
                          '          "defaultConfiguration": "development"\n'
                          '        },\n'
                          '        "test": {\n'
                          '          "builder": "@angular/build:unit-test",\n'
                          '          "options": {\n'
                          '            "tsConfig": "tsconfig.spec.json",\n'
                          '            "buildTarget": "workplace-agent-ui:build:development"\n'
                          '          }\n'
                          '        },\n'
                          '        "lint": {\n'
                          '          "builder": "@angular-eslint/builder:lint",\n'
                          '          "options": {\n'
                          '            "lintFilePatterns": [\n'
                          '              "src/**/*.ts",\n'
                          '              "src/**/*.html",\n'
                          '              "e2e/**/*.ts"\n'
                          '            ]\n'
                          '          }\n'
                          '        }\n'
                          '      }\n'
                          '    }\n'
                          '  }\n'
                          '}\n',
 'frontend/docs/API_CLIENT.md': '# Angular API client\n'
                                '\n'
                                '`WorkplaceAgentApiService` covers all 31 endpoint method/path pairs recorded in Phase '
                                '0: health, readiness, capabilities, organization reads, Nucleus reads, generic '
                                'resource reads, natural-language query, and the governed proposal lifecycle.\n'
                                '\n'
                                'All incoming payloads are parsed through Zod. Invalid success payloads fail closed '
                                'before reaching components. The API error interceptor converts the backend envelope '
                                'into `WorkplaceApiError`, preserving `X-Request-Id` correlation.\n'
                                '\n'
                                'The mock user is read from runtime configuration by `CurrentUserStore` and attached '
                                'only to requests whose URL begins with the configured API base URL.\n',
 'frontend/docs/PHASE_1_ACCEPTANCE.md': '# Phase 1 acceptance\n'
                                        '\n'
                                        'Phase 1 is complete when:\n'
                                        '\n'
                                        '- `npm install` succeeds and creates `package-lock.json`.\n'
                                        '- `npm run validate:phase1` passes.\n'
                                        '- the Angular production build respects bundle budgets.\n'
                                        '- all 31 backend operations are represented by one facade.\n'
                                        '- runtime configuration rejects unknown or malformed fields.\n'
                                        '- success and error payloads are validated at runtime.\n'
                                        '- no component or feature service issues raw HTTP requests.\n'
                                        '- mock identity and request IDs are attached by functional interceptors.\n'
                                        '- Vitest unit tests and Playwright test discovery pass.\n'
                                        '- the placeholder shell works at desktop and compact widths.\n'
                                        '- no fake stream, fake reasoning, or fake execution behavior exists.\n',
 'frontend/docs/PHASE_1_ARCHITECTURE.md': '# Phase 1 Angular architecture\n'
                                          '\n'
                                          'Phase 1 creates a native Angular 21 LTS application using standalone '
                                          'components, strict TypeScript, zoneless change detection, Signals for local '
                                          'identity state, RxJS for HTTP flows, Zod at every network boundary, Vitest, '
                                          'and Playwright.\n'
                                          '\n'
                                          '## Boundary rules\n'
                                          '\n'
                                          '1. `WorkplaceAgentApiService` is the only feature-facing backend facade.\n'
                                          '2. `ValidatedHttpService` is the only class allowed to inject '
                                          '`HttpClient`.\n'
                                          '3. Components never know endpoint strings.\n'
                                          '4. Functional interceptors own request IDs, sandbox identity, and error '
                                          'conversion.\n'
                                          '5. Runtime configuration is fetched and validated before Angular '
                                          'bootstraps.\n'
                                          '6. No risk, approval, organization-scope, or execution decision is '
                                          'calculated in the browser.\n'
                                          '7. Streaming remains explicitly unavailable; Phase 1 does not simulate it.\n'
                                          '\n'
                                          '## Version choice\n'
                                          '\n'
                                          'Angular 21 LTS is selected instead of Angular 22 because it supports Node '
                                          '20.19, 22.12, and 24 while retaining modern standalone, zoneless and Vitest '
                                          'defaults. Dependencies are exact-pinned; `npm install` creates the lockfile '
                                          'in the target repository.\n',
 'frontend/docs/TESTING.md': '# Frontend validation\n'
                             '\n'
                             '```bash\n'
                             'cd frontend\n'
                             'npm install\n'
                             'npm run validate:phase1\n'
                             'npx playwright install chromium\n'
                             'npm run e2e\n'
                             '```\n'
                             '\n'
                             '`validate:phase1` runs architecture-boundary checks, strict application and test type '
                             'checks, Angular-aware ESLint, Vitest, a production build, and Playwright test discovery. '
                             'Browser installation is kept explicit because Playwright browser binaries are '
                             'platform-specific.\n',
 'frontend/e2e/foundation.spec.ts': "import { expect, test } from '@playwright/test';\n"
                                    '\n'
                                    "test('loads the Phase 1 foundation without exposing raw endpoint controls', async "
                                    '({ page }) => {\n'
                                    "  await page.goto('/');\n"
                                    "  await expect(page.getByRole('heading', {name:'Frontend foundation "
                                    "ready'})).toBeVisible();\n"
                                    "  await expect(page.getByRole('complementary', {name:'Ask AI "
                                    "placeholder'})).toBeVisible();\n"
                                    '  await '
                                    "expect(page.locator('body')).not.toContainText('/agent/actions/propose');\n"
                                    '});\n',
 'frontend/eslint.config.mjs': "import eslint from '@eslint/js';\n"
                               "import angular from 'angular-eslint';\n"
                               "import tseslint from 'typescript-eslint';\n"
                               '\n'
                               'export default tseslint.config(\n'
                               "  { ignores: ['dist/**', 'node_modules/**', 'playwright-report/**', 'test-results/**'] "
                               '},\n'
                               '  {\n'
                               "    files: ['src/**/*.ts'],\n"
                               '    extends: [eslint.configs.recommended, ...tseslint.configs.recommendedTypeChecked, '
                               '...angular.configs.tsRecommended],\n'
                               '    processor: angular.processInlineTemplates,\n'
                               '    languageOptions: { parserOptions: { projectService: true, tsconfigRootDir: '
                               'import.meta.dirname } },\n'
                               '    rules: {\n'
                               "      '@angular-eslint/component-selector': ['error', { type: 'element', prefix: "
                               "'app', style: 'kebab-case' }],\n"
                               "      '@angular-eslint/directive-selector': ['error', { type: 'attribute', prefix: "
                               "'app', style: 'camelCase' }],\n"
                               "      '@typescript-eslint/consistent-type-imports': ['error', { prefer: 'type-imports' "
                               '}],\n'
                               "      '@typescript-eslint/no-explicit-any': 'error',\n"
                               "      '@typescript-eslint/no-floating-promises': 'error'\n"
                               '    }\n'
                               '  },\n'
                               '  {\n'
                               "    files: ['src/**/*.html'],\n"
                               '    extends: [...angular.configs.templateRecommended, '
                               '...angular.configs.templateAccessibility]\n'
                               '  },\n'
                               '  {\n'
                               "    files: ['e2e/**/*.ts'],\n"
                               '    extends: [eslint.configs.recommended, ...tseslint.configs.recommended],\n'
                               "    languageOptions: { parserOptions: { project: './tsconfig.e2e.json', "
                               'tsconfigRootDir: import.meta.dirname } }\n'
                               '  }\n'
                               ');\n',
 'frontend/package.json': '{\n'
                          '  "name": "dbmr-workplace-agent-ui",\n'
                          '  "version": "0.1.0",\n'
                          '  "private": true,\n'
                          '  "description": "Angular presentation layer for the governed DBMR Workplace Agent '
                          'sandbox",\n'
                          '  "engines": {\n'
                          '    "node": "^20.19.0 || ^22.12.0 || ^24.0.0",\n'
                          '    "npm": ">=10"\n'
                          '  },\n'
                          '  "scripts": {\n'
                          '    "start": "ng serve --host 127.0.0.1 --port 4200",\n'
                          '    "build": "ng build",\n'
                          '    "build:development": "ng build --configuration development",\n'
                          '    "typecheck": "tsc -p tsconfig.app.json --noEmit && tsc -p tsconfig.spec.json --noEmit '
                          '&& tsc -p tsconfig.e2e.json --noEmit",\n'
                          '    "lint": "eslint \\"src/**/*.ts\\" \\"src/**/*.html\\" \\"e2e/**/*.ts\\"",\n'
                          '    "test": "ng test --watch=false",\n'
                          '    "test:coverage": "ng test --watch=false --coverage",\n'
                          '    "e2e": "playwright test",\n'
                          '    "e2e:list": "playwright test --list",\n'
                          '    "quality:boundaries": "node scripts/check-architecture-boundaries.mjs",\n'
                          '    "validate:phase1": "npm run quality:boundaries && npm run typecheck && npm run lint && '
                          'npm run test && npm run build && npm run e2e:list",\n'
                          '    "validate:full": "npm run validate:phase1 && npm run e2e"\n'
                          '  },\n'
                          '  "dependencies": {\n'
                          '    "@angular/cdk": "21.2.14",\n'
                          '    "@angular/common": "21.2.18",\n'
                          '    "@angular/compiler": "21.2.18",\n'
                          '    "@angular/core": "21.2.18",\n'
                          '    "@angular/forms": "21.2.18",\n'
                          '    "@angular/platform-browser": "21.2.18",\n'
                          '    "@angular/router": "21.2.18",\n'
                          '    "rxjs": "7.8.2",\n'
                          '    "tslib": "2.8.1",\n'
                          '    "zod": "4.4.3"\n'
                          '  },\n'
                          '  "devDependencies": {\n'
                          '    "@angular/build": "21.2.18",\n'
                          '    "@angular/cli": "21.2.18",\n'
                          '    "@angular/compiler-cli": "21.2.18",\n'
                          '    "@eslint/js": "9.39.1",\n'
                          '    "@playwright/test": "1.61.1",\n'
                          '    "@types/node": "24.3.0",\n'
                          '    "angular-eslint": "21.2.0",\n'
                          '    "eslint": "9.39.1",\n'
                          '    "jsdom": "27.0.1",\n'
                          '    "typescript": "5.9.3",\n'
                          '    "typescript-eslint": "8.46.2",\n'
                          '    "vitest": "4.1.10"\n'
                          '  }\n'
                          '}\n',
 'frontend/playwright.config.ts': "import { defineConfig, devices } from '@playwright/test';\n"
                                  '\n'
                                  'export default defineConfig({\n'
                                  "  testDir: './e2e',\n"
                                  '  fullyParallel: true,\n'
                                  "  forbidOnly: Boolean(process.env['CI']),\n"
                                  "  retries: process.env['CI'] ? 2 : 0,\n"
                                  "  reporter: [['html', { open: 'never' }]],\n"
                                  "  use: { baseURL: 'http://127.0.0.1:4200', trace: 'on-first-retry' },\n"
                                  "  webServer: { command: 'npm run start', url: 'http://127.0.0.1:4200', "
                                  "reuseExistingServer: !process.env['CI'], timeout: 120000 },\n"
                                  '  projects: [\n'
                                  "    { name:'chromium-desktop', use:{...devices['Desktop Chrome'], "
                                  'viewport:{width:1365,height:647}} },\n'
                                  "    { name:'chromium-compact', use:{...devices['Desktop Chrome'], "
                                  'viewport:{width:680,height:900}} }\n'
                                  '  ]\n'
                                  '});\n',
 'frontend/public/config/app-config.json': '{\n'
                                           '  "apiBaseUrl": "http://127.0.0.1:8000",\n'
                                           '  "defaultOrganizationId": "org_sandbox_001",\n'
                                           '  "mockUserId": "usr_admin_001",\n'
                                           '  "requestTimeoutMs": 30000,\n'
                                           '  "enableDebugViews": false,\n'
                                           '  "streamTransport": "rest"\n'
                                           '}\n',
 'frontend/scripts/check-architecture-boundaries.mjs': "import { readdir, readFile } from 'node:fs/promises';\n"
                                                       "import { relative } from 'node:path';\n"
                                                       "import { fileURLToPath } from 'node:url';\n"
                                                       '\n'
                                                       "const root = new URL('../src/app/', import.meta.url);\n"
                                                       'const rootPath = fileURLToPath(root);\n'
                                                       'const allowedHttpFiles = new '
                                                       "Set(['core/api/validated-http.service.ts']);\n"
                                                       'const violations = [];\n'
                                                       '\n'
                                                       'async function walk(url) {\n'
                                                       '  for (const entry of await readdir(url, { withFileTypes: true '
                                                       '})) {\n'
                                                       '    const child = new URL(`${entry.name}${entry.isDirectory() '
                                                       "? '/' : ''}`, url);\n"
                                                       '    if (entry.isDirectory()) {\n'
                                                       '      await walk(child);\n'
                                                       '      continue;\n'
                                                       '    }\n'
                                                       "    if (!entry.name.endsWith('.ts') || "
                                                       "entry.name.endsWith('.spec.ts')) continue;\n"
                                                       '    const path = relative(rootPath, '
                                                       "fileURLToPath(child)).replaceAll('\\\\', '/');\n"
                                                       "    const text = await readFile(child, 'utf8');\n"
                                                       '    if ((/\\bHttpClient\\b/.test(text) || '
                                                       '/\\bfetch\\s*\\(/.test(text)) && !allowedHttpFiles.has(path) '
                                                       "&& !path.startsWith('core/config/')) {\n"
                                                       '      violations.push(`${path}: raw HTTP boundary`);\n'
                                                       '    }\n'
                                                       '    if (/(:\\s*any\\b|<any>)/.test(text)) '
                                                       'violations.push(`${path}: explicit any`);\n'
                                                       '  }\n'
                                                       '}\n'
                                                       '\n'
                                                       'await walk(root);\n'
                                                       'if (violations.length) {\n'
                                                       "  console.error(violations.join('\\n'));\n"
                                                       '  process.exit(1);\n'
                                                       '}\n'
                                                       "console.log('Angular architecture boundaries are valid.');\n",
 'frontend/src/app/app.component.html': '<a class="skip-link" href="#main-content">Skip to content</a>\n'
                                        '<div class="foundation-shell">\n'
                                        '  <header class="foundation-header">\n'
                                        '    <strong>DBMR Workplace Agent</strong>\n'
                                        '    <span>Angular foundation</span>\n'
                                        '  </header>\n'
                                        '  <aside class="foundation-sidebar" aria-label="Primary navigation">\n'
                                        '    <p>Navigation shell reserved for Phase 3.</p>\n'
                                        '  </aside>\n'
                                        '  <main id="main-content" class="foundation-main" tabindex="-1">\n'
                                        '    <h1>Frontend foundation ready</h1>\n'
                                        '    <p>The application is bootstrapped with strict runtime configuration, '
                                        'validated API contracts, and a single backend facade.</p>\n'
                                        '    <dl>\n'
                                        '      <div><dt>API</dt><dd>{{ apiBaseUrl }}</dd></div>\n'
                                        "      <div><dt>Organization</dt><dd>{{ organizationId ?? 'Not configured' "
                                        '}}</dd></div>\n'
                                        "      <div><dt>Sandbox user</dt><dd>{{ currentUser.userId() ?? 'Not "
                                        "configured' }}</dd></div>\n"
                                        '    </dl>\n'
                                        '  </main>\n'
                                        '  <aside class="foundation-assistant" aria-label="Ask AI placeholder">\n'
                                        '    <h2>Ask AI</h2>\n'
                                        '    <p>The interactive panel is implemented in Phase 4.</p>\n'
                                        '  </aside>\n'
                                        '</div>\n'
                                        '<div class="sr-only" aria-live="polite" aria-atomic="true"></div>\n',
 'frontend/src/app/app.component.scss': ':host { display: block; min-height: 100vh; }\n'
                                        '.skip-link { position: fixed; z-index: 100; left: 12px; top: 8px; transform: '
                                        'translateY(-160%); background: #111; color: #fff; padding: 8px 12px; '
                                        'border-radius: 6px; }\n'
                                        '.skip-link:focus { transform: translateY(0); }\n'
                                        '.foundation-shell { min-height: 100vh; display: grid; grid-template-columns: '
                                        '240px minmax(360px, 1fr) 420px; grid-template-rows: 56px 1fr; '
                                        'grid-template-areas: "header header header" "sidebar main assistant"; }\n'
                                        '.foundation-header { grid-area: header; display: flex; align-items: center; '
                                        'justify-content: space-between; padding: 0 20px; background: #fff; '
                                        'border-top: 4px solid #f6821f; border-bottom: 1px solid #dedfe3; }\n'
                                        '.foundation-sidebar { grid-area: sidebar; padding: 20px; background: #f2f2f3; '
                                        'border-right: 1px solid #dedfe3; }\n'
                                        '.foundation-main { grid-area: main; padding: 48px; background: #fff; }\n'
                                        '.foundation-assistant { grid-area: assistant; padding: 20px; border-left: 1px '
                                        'solid #dedfe3; background-color: #fafafa; background-image: '
                                        'radial-gradient(#d7d7d9 0.7px, transparent 0.7px); background-size: 12px '
                                        '12px; }\n'
                                        'h1 { margin-top: 0; font-size: clamp(1.8rem, 3vw, 2.6rem); }\n'
                                        'dl { display: grid; gap: 10px; max-width: 600px; }\n'
                                        'dl div { display: grid; grid-template-columns: 130px 1fr; gap: 16px; }\n'
                                        'dt { color: #666970; } dd { margin: 0; overflow-wrap: anywhere; }\n'
                                        '@media (max-width: 1000px) { .foundation-shell { grid-template-columns: 210px '
                                        '1fr; grid-template-areas: "header header" "sidebar main"; } '
                                        '.foundation-assistant { display: none; } }\n'
                                        '@media (max-width: 700px) { .foundation-shell { grid-template-columns: 1fr; '
                                        'grid-template-areas: "header" "main"; } .foundation-sidebar { display: none; '
                                        '} .foundation-main { padding: 28px 20px; } }\n',
 'frontend/src/app/app.component.spec.ts': "import { TestBed } from '@angular/core/testing';\n"
                                           "import { describe, expect, it } from 'vitest';\n"
                                           "import { AppComponent } from './app.component';\n"
                                           "import { APP_RUNTIME_CONFIG } from './core/config/app-config.token';\n"
                                           '\n'
                                           "describe('AppComponent', () => {\n"
                                           "  it('renders the foundation state', async () => {\n"
                                           '    await '
                                           "TestBed.configureTestingModule({imports:[AppComponent],providers:[{provide:APP_RUNTIME_CONFIG,useValue:{apiBaseUrl:'http://api.test',defaultOrganizationId:'org_1',mockUserId:'usr_1',requestTimeoutMs:30000,enableDebugViews:false,streamTransport:'rest'}}]}).compileComponents();\n"
                                           '    const fixture=TestBed.createComponent(AppComponent); '
                                           'fixture.detectChanges();\n'
                                           '    const element = fixture.nativeElement as HTMLElement;\n'
                                           "    expect(element.textContent).toContain('Frontend foundation ready');\n"
                                           '  });\n'
                                           '});\n',
 'frontend/src/app/app.component.ts': "import { ChangeDetectionStrategy, Component, inject } from '@angular/core';\n"
                                      "import { APP_RUNTIME_CONFIG } from './core/config/app-config.token';\n"
                                      "import { CurrentUserStore } from './core/auth/current-user.store';\n"
                                      '\n'
                                      '@Component({\n'
                                      "  selector: 'app-root',\n"
                                      '  changeDetection: ChangeDetectionStrategy.OnPush,\n'
                                      "  templateUrl: './app.component.html',\n"
                                      "  styleUrl: './app.component.scss'\n"
                                      '})\n'
                                      'export class AppComponent {\n'
                                      '  private readonly runtimeConfig = inject(APP_RUNTIME_CONFIG);\n'
                                      '  readonly currentUser = inject(CurrentUserStore);\n'
                                      '  readonly apiBaseUrl = this.runtimeConfig.apiBaseUrl;\n'
                                      '  readonly organizationId = this.runtimeConfig.defaultOrganizationId;\n'
                                      '}\n',
 'frontend/src/app/app.config.ts': "import { provideHttpClient, withInterceptors } from '@angular/common/http';\n"
                                   'import { type ApplicationConfig, provideZonelessChangeDetection } from '
                                   "'@angular/core';\n"
                                   "import { provideRouter } from '@angular/router';\n"
                                   "import { routes } from './app.routes';\n"
                                   "import { apiErrorInterceptor } from './core/api/api-error.interceptor';\n"
                                   "import { requestIdInterceptor } from './core/api/request-id.interceptor';\n"
                                   "import { authHeaderInterceptor } from './core/auth/auth-header.interceptor';\n"
                                   "import type { AppRuntimeConfig } from './core/config/app-config.model';\n"
                                   "import { APP_RUNTIME_CONFIG } from './core/config/app-config.token';\n"
                                   '\n'
                                   'export function createAppConfig(runtimeConfig: AppRuntimeConfig): '
                                   'ApplicationConfig {\n'
                                   '  return {\n'
                                   '    providers: [\n'
                                   '      provideZonelessChangeDetection(),\n'
                                   '      provideRouter(routes),\n'
                                   '      { provide: APP_RUNTIME_CONFIG, useValue: runtimeConfig },\n'
                                   '      provideHttpClient(withInterceptors([requestIdInterceptor, '
                                   'authHeaderInterceptor, apiErrorInterceptor]))\n'
                                   '    ]\n'
                                   '  };\n'
                                   '}\n',
 'frontend/src/app/app.routes.ts': "import type { Routes } from '@angular/router';\n"
                                   '\n'
                                   'export const routes: Routes = [];\n',
 'frontend/src/app/core/api/api-error.interceptor.ts': 'import { HttpErrorResponse, type HttpInterceptorFn } from '
                                                       "'@angular/common/http';\n"
                                                       "import { catchError, throwError } from 'rxjs';\n"
                                                       'import { WorkplaceApiError } from '
                                                       "'../errors/workplace-api.error';\n"
                                                       "import { errorEnvelopeSchema } from './wire.schemas';\n"
                                                       '\n'
                                                       'export const apiErrorInterceptor: HttpInterceptorFn = '
                                                       '(request, next) => next(request).pipe(\n'
                                                       '  catchError((error: unknown) => {\n'
                                                       '    if (error instanceof WorkplaceApiError) return '
                                                       'throwError(() => error);\n'
                                                       '    if (error instanceof HttpErrorResponse) {\n'
                                                       '      const parsed = '
                                                       'errorEnvelopeSchema.safeParse(error.error);\n'
                                                       '      if (parsed.success) {\n'
                                                       '        return throwError(() => new '
                                                       'WorkplaceApiError(error.status, parsed.data.error.code, '
                                                       'parsed.data.error.message, parsed.data.error.request_id, '
                                                       'error));\n'
                                                       '      }\n'
                                                       "      const requestId = error.headers?.get('X-Request-Id') ?? "
                                                       'undefined;\n'
                                                       "      const message = error.status === 0 ? 'The backend could "
                                                       "not be reached.' : 'The server returned an unexpected error "
                                                       "response.';\n"
                                                       '      return throwError(() => new '
                                                       "WorkplaceApiError(error.status, 'unexpected_response', "
                                                       'message, requestId, error));\n'
                                                       '    }\n'
                                                       '    return throwError(() => new WorkplaceApiError(0, '
                                                       "'network_error', 'The request failed before a response was "
                                                       "received.', undefined, error));\n"
                                                       '  })\n'
                                                       ');\n',
 'frontend/src/app/core/api/endpoint-count.ts': 'export const PHASE_1_API_METHOD_COUNT = 31 as const;\n',
 'frontend/src/app/core/api/request-id.interceptor.ts': 'import type { HttpInterceptorFn } from '
                                                        "'@angular/common/http';\n"
                                                        "import { inject } from '@angular/core';\n"
                                                        'import { APP_RUNTIME_CONFIG } from '
                                                        "'../config/app-config.token';\n"
                                                        '\n'
                                                        'function createRequestId(): string {\n'
                                                        '  return globalThis.crypto?.randomUUID?.() ?? '
                                                        '`web-${Date.now()}-${Math.random().toString(16).slice(2)}`;\n'
                                                        '}\n'
                                                        '\n'
                                                        'export const requestIdInterceptor: HttpInterceptorFn = '
                                                        '(request, next) => {\n'
                                                        '  const config = inject(APP_RUNTIME_CONFIG);\n'
                                                        '  if (!request.url.startsWith(config.apiBaseUrl) || '
                                                        "request.headers.has('X-Request-Id')) {\n"
                                                        '    return next(request);\n'
                                                        '  }\n'
                                                        "  return next(request.clone({ setHeaders: { 'X-Request-Id': "
                                                        'createRequestId() } }));\n'
                                                        '};\n',
 'frontend/src/app/core/api/validated-http.service.ts': 'import { HttpClient, type HttpParams } from '
                                                        "'@angular/common/http';\n"
                                                        "import { inject, Injectable } from '@angular/core';\n"
                                                        'import { catchError, map, throwError, timeout, TimeoutError, '
                                                        "type Observable } from 'rxjs';\n"
                                                        "import type { ZodType } from 'zod';\n"
                                                        'import { APP_RUNTIME_CONFIG } from '
                                                        "'../config/app-config.token';\n"
                                                        'import { WorkplaceApiError } from '
                                                        "'../errors/workplace-api.error';\n"
                                                        '\n'
                                                        "@Injectable({ providedIn: 'root' })\n"
                                                        'export class ValidatedHttpService {\n'
                                                        '  private readonly http = inject(HttpClient);\n'
                                                        '  private readonly config = inject(APP_RUNTIME_CONFIG);\n'
                                                        '\n'
                                                        '  request<T>(\n'
                                                        "    method: 'GET' | 'POST',\n"
                                                        '    path: string,\n'
                                                        '    schema: ZodType<T>,\n'
                                                        '    options: { body?: unknown; params?: HttpParams } = {}\n'
                                                        '  ): Observable<T> {\n'
                                                        '    return this.http\n'
                                                        '      .request<unknown>(method, '
                                                        '`${this.config.apiBaseUrl}${path}`, {\n'
                                                        '        body: options.body,\n'
                                                        '        params: options.params\n'
                                                        '      })\n'
                                                        '      .pipe(\n'
                                                        '        timeout(this.config.requestTimeoutMs),\n'
                                                        '        map((payload) => {\n'
                                                        '          const parsed = schema.safeParse(payload);\n'
                                                        '          if (!parsed.success) {\n'
                                                        '            throw new WorkplaceApiError(\n'
                                                        '              502,\n'
                                                        "              'invalid_success_payload',\n"
                                                        "              'The server returned an unexpected success "
                                                        "payload.',\n"
                                                        '              undefined,\n'
                                                        '              parsed.error\n'
                                                        '            );\n'
                                                        '          }\n'
                                                        '          return parsed.data;\n'
                                                        '        }),\n'
                                                        '        catchError((error: unknown) => {\n'
                                                        '          if (error instanceof WorkplaceApiError) {\n'
                                                        '            return throwError(() => error);\n'
                                                        '          }\n'
                                                        '          if (error instanceof TimeoutError) {\n'
                                                        '            return throwError(\n'
                                                        '              () =>\n'
                                                        '                new WorkplaceApiError(\n'
                                                        '                  408,\n'
                                                        "                  'request_timeout',\n"
                                                        "                  'The request did not complete before the "
                                                        "configured timeout.',\n"
                                                        '                  undefined,\n'
                                                        '                  error\n'
                                                        '                )\n'
                                                        '            );\n'
                                                        '          }\n'
                                                        '          return throwError(() => error);\n'
                                                        '        })\n'
                                                        '      );\n'
                                                        '  }\n'
                                                        '}\n',
 'frontend/src/app/core/api/wire.models.ts': "import type { z } from 'zod';\n"
                                             'import {\n'
                                             '  actionApprovalResponseSchema, actionDecisionRequestSchema, '
                                             'actionExecutionRequestSchema, actionExecutionResponseSchema, '
                                             'actionProposalListResponseSchema, actionProposalRequestSchema, '
                                             'actionProposalResponseSchema, actionStatusFilterSchema,\n'
                                             '  agentQueryResponseSchema, auditLogResponseSchema, '
                                             'capabilitiesResponseSchema, healthSchema, nucleusAccountResponseSchema,\n'
                                             '  nucleusApprovalStatusResponseSchema, '
                                             'nucleusEntitlementsResponseSchema, nucleusLicenseResponseSchema, '
                                             'organizationOverviewResponseSchema,\n'
                                             '  organizationProfileResponseSchema, organizationReportsResponseSchema, '
                                             'organizationSeatsResponseSchema, organizationUsersResponseSchema,\n'
                                             '  readinessDetailsSchema, readinessSchema, reportAccessResponseSchema, '
                                             'workplaceResourceCountResponseSchema, workplaceResourceResponseSchema,\n'
                                             '  workplaceResourceSchemaResponseSchema, '
                                             'workplaceResourceSearchRequestSchema, '
                                             'workplaceResourceSearchResponseSchema, '
                                             'workplaceResourceTypeListResponseSchema\n'
                                             "} from './wire.schemas';\n"
                                             '\n'
                                             'export type HealthResponse = z.infer<typeof healthSchema>;\n'
                                             'export type ReadinessResponse = z.infer<typeof readinessSchema>;\n'
                                             'export type ReadinessDetailsResponse = z.infer<typeof '
                                             'readinessDetailsSchema>;\n'
                                             'export type CapabilitiesResponse = z.infer<typeof '
                                             'capabilitiesResponseSchema>;\n'
                                             'export type OrganizationOverviewResponse = z.infer<typeof '
                                             'organizationOverviewResponseSchema>;\n'
                                             'export type OrganizationProfileResponse = z.infer<typeof '
                                             'organizationProfileResponseSchema>;\n'
                                             'export type OrganizationUsersResponse = z.infer<typeof '
                                             'organizationUsersResponseSchema>;\n'
                                             'export type OrganizationSeatsResponse = z.infer<typeof '
                                             'organizationSeatsResponseSchema>;\n'
                                             'export type OrganizationReportsResponse = z.infer<typeof '
                                             'organizationReportsResponseSchema>;\n'
                                             'export type ReportAccessResponse = z.infer<typeof '
                                             'reportAccessResponseSchema>;\n'
                                             'export type AuditLogResponse = z.infer<typeof auditLogResponseSchema>;\n'
                                             'export type NucleusAccountResponse = z.infer<typeof '
                                             'nucleusAccountResponseSchema>;\n'
                                             'export type NucleusLicenseResponse = z.infer<typeof '
                                             'nucleusLicenseResponseSchema>;\n'
                                             'export type NucleusApprovalStatusResponse = z.infer<typeof '
                                             'nucleusApprovalStatusResponseSchema>;\n'
                                             'export type NucleusEntitlementsResponse = z.infer<typeof '
                                             'nucleusEntitlementsResponseSchema>;\n'
                                             'export type WorkplaceResourceSearchRequest = z.input<typeof '
                                             'workplaceResourceSearchRequestSchema>;\n'
                                             'export type WorkplaceResourceTypeListResponse = z.infer<typeof '
                                             'workplaceResourceTypeListResponseSchema>;\n'
                                             'export type WorkplaceResourceSchemaResponse = z.infer<typeof '
                                             'workplaceResourceSchemaResponseSchema>;\n'
                                             'export type WorkplaceResourceSearchResponse = z.infer<typeof '
                                             'workplaceResourceSearchResponseSchema>;\n'
                                             'export type WorkplaceResourceCountResponse = z.infer<typeof '
                                             'workplaceResourceCountResponseSchema>;\n'
                                             'export type WorkplaceResourceResponse = z.infer<typeof '
                                             'workplaceResourceResponseSchema>;\n'
                                             'export type AgentQueryResponse = z.infer<typeof '
                                             'agentQueryResponseSchema>;\n'
                                             'export type AgentActionProposalResponse = z.infer<typeof '
                                             'actionProposalResponseSchema>;\n'
                                             'export type AgentActionProposalListResponse = z.infer<typeof '
                                             'actionProposalListResponseSchema>;\n'
                                             'export type AgentActionApprovalResponse = z.infer<typeof '
                                             'actionApprovalResponseSchema>;\n'
                                             'export type AgentActionExecutionResponse = z.infer<typeof '
                                             'actionExecutionResponseSchema>;\n'
                                             '\n'
                                             'export type AgentActionProposalRequest = z.input<typeof '
                                             'actionProposalRequestSchema>;\n'
                                             'export type AgentActionDecisionRequest = z.input<typeof '
                                             'actionDecisionRequestSchema>;\n'
                                             'export type AgentActionExecutionRequest = z.input<typeof '
                                             'actionExecutionRequestSchema>;\n'
                                             'export interface AgentActionListFilters { status?: z.input<typeof '
                                             'actionStatusFilterSchema>; actionName?: z.input<typeof '
                                             "actionProposalRequestSchema>['action_name']; requestedBy?: string; "
                                             'limit?: number; cursor?: string; }\n',
 'frontend/src/app/core/api/wire.schemas.spec.ts': "import { describe, expect, it } from 'vitest';\n"
                                                   'import { agentQueryResponseSchema, errorEnvelopeSchema, '
                                                   "workplaceResourceSearchRequestSchema } from './wire.schemas';\n"
                                                   '\n'
                                                   "describe('wire schemas', () => {\n"
                                                   "  it('rejects a read response carrying an action proposal', () => "
                                                   '{\n'
                                                   '    const parsed = agentQueryResponseSchema.safeParse({ '
                                                   "mode:'read', organization_id:'org', answer:'x', evidence_ids:[], "
                                                   "answer_source:'deterministic', results:[], action_proposal:{}, "
                                                   'missing_fields:[] });\n'
                                                   '    expect(parsed.success).toBe(false);\n'
                                                   '  });\n'
                                                   "  it('validates the canonical error envelope', () => {\n"
                                                   '    '
                                                   "expect(errorEnvelopeSchema.parse({error:{code:'permission_denied',message:'Denied',request_id:'req_1'}}).error.code).toBe('permission_denied');\n"
                                                   '  });\n'
                                                   "  it('applies safe resource-search defaults', () => {\n"
                                                   '    '
                                                   'expect(workplaceResourceSearchRequestSchema.parse({filters:{}})).toEqual({filters:{},sort_by:null,descending:false,limit:50,offset:0});\n'
                                                   '  });\n'
                                                   '});\n',
 'frontend/src/app/core/api/wire.schemas.ts': "import { z } from 'zod';\n"
                                              '\n'
                                              'export const isoDateTimeSchema = z.iso.datetime({ offset: true });\n'
                                              'const nullableDateTime = isoDateTimeSchema.nullable();\n'
                                              'const jsonObject = z.record(z.string(), z.unknown());\n'
                                              '\n'
                                              'export const errorEnvelopeSchema = z.object({ error: z.object({ code: '
                                              'z.string().min(1), message: z.string(), request_id: z.string().min(1) '
                                              '}).strict() }).strict();\n'
                                              'export const healthSchema = z.object({ status: z.string() '
                                              '}).passthrough();\n'
                                              'export const readinessSchema = z.object({ status: z.string(), database: '
                                              'z.string(), environment: z.string() }).passthrough();\n'
                                              'export const readinessDetailsSchema = z.object({ status: z.string(), '
                                              'checks: z.record(z.string(), z.boolean()), migration: jsonObject, '
                                              'actions: jsonObject, read_tools: jsonObject, audit: jsonObject, limits: '
                                              'jsonObject, model: jsonObject, raw_mock_api_enabled: z.boolean() '
                                              '}).passthrough();\n'
                                              '\n'
                                              'export const accessSchema = z.object({ user_id: z.string(), permission: '
                                              'z.string() }).strict();\n'
                                              'export const organizationSchema = z.object({ id: z.string(), '
                                              'display_name: z.string(), legal_name: z.string().nullable(), '
                                              'contact_email: z.string().nullable(), environment: '
                                              "z.enum(['sandbox','production']), status: "
                                              "z.enum(['active','suspended']), version: z.number().int().nonnegative() "
                                              '}).strict();\n'
                                              'export const organizationProfileResponseSchema = z.object({ '
                                              'organization: organizationSchema, access: accessSchema }).strict();\n'
                                              'export const organizationOverviewResponseSchema = z.object({ '
                                              'organization: organizationSchema.extend({ organization_type: '
                                              'z.string(), renewal_date: z.iso.date().nullable(), workspace_status: '
                                              "z.enum(['healthy','degraded','unavailable','unknown']) }), metrics: "
                                              'z.object({ licensed_modules:z.number().int().nonnegative(), '
                                              'available_areas:z.number().int().nonnegative(), '
                                              'organization_logins:z.number().int().nonnegative(), '
                                              'workspace_health_percent:z.number().int().min(0).max(100) }), '
                                              'overview_version:z.number().int().positive(), '
                                              'overview_updated_at:nullableDateTime, access:accessSchema, '
                                              'generated_at:isoDateTimeSchema }).strict();\n'
                                              '\n'
                                              'const memberSchema = z.object({ user_id:z.string(), '
                                              'display_name:z.string(), email:z.string(), '
                                              "user_status:z.enum(['active','disabled']), role:z.string(), "
                                              "membership_status:z.enum(['invited','active','suspended','removed']), "
                                              'has_active_seat:z.boolean(), joined_at:nullableDateTime }).strict();\n'
                                              'export const organizationUsersResponseSchema = z.object({ '
                                              'organization_id:z.string(), members:z.array(memberSchema), '
                                              'access:accessSchema }).strict();\n'
                                              'export const organizationSeatsResponseSchema = z.object({ '
                                              'organization_id:z.string(), seats:z.object({ '
                                              "organization_id:z.string(), seat_type:z.literal('standard'), "
                                              'total_seats:z.number().int().nonnegative(), '
                                              'active_assignments:z.number().int().nonnegative(), '
                                              'available_seats:z.number().int().nonnegative(), '
                                              'seated_user_ids:z.array(z.string()) }).strict(), access:accessSchema '
                                              '}).strict();\n'
                                              'const reportSchema = z.object({ id:z.string(), '
                                              'external_report_id:z.string(), title:z.string(), '
                                              "market_name:z.string().nullable(), status:z.enum(['active','retired']) "
                                              '}).strict();\n'
                                              'const accessLevel = '
                                              "z.enum(['view','chat','download','full']).nullable();\n"
                                              'const reportAccessStatus = '
                                              "z.enum(['active','suspended','expired','revoked']).nullable();\n"
                                              'export const organizationReportsResponseSchema = z.object({ '
                                              'organization_id:z.string(), reports:z.array(z.object({ '
                                              'report:reportSchema, has_access:z.boolean(), access_level:accessLevel, '
                                              'access_status:reportAccessStatus }).strict()), access:accessSchema '
                                              '}).strict();\n'
                                              'export const reportAccessResponseSchema = z.object({ '
                                              'organization_id:z.string(), report_id:z.string(), '
                                              'has_access:z.boolean(), access_level:accessLevel, '
                                              'access_status:reportAccessStatus, access:accessSchema }).strict();\n'
                                              'const auditEventSchema = z.object({ id:z.string(), '
                                              'actor_user_id:z.string(), organization_id:z.string(), '
                                              'event_type:z.string(), operation:z.string(), outcome:z.string(), '
                                              'resource_type:z.string(), resource_id:z.string(), '
                                              'details:jsonObject.nullable(), created_at:nullableDateTime '
                                              '}).strict();\n'
                                              'export const auditLogResponseSchema = z.object({ '
                                              'organization_id:z.string(), events:z.array(auditEventSchema) '
                                              '}).strict();\n'
                                              '\n'
                                              'const nucleusAccount = z.object({ '
                                              'organization_account_id:z.number().int(), organization_name:z.string(), '
                                              'organization_code:z.string().nullable(), '
                                              'organization_type:z.string().nullable(), '
                                              'industry:z.string().nullable(), website:z.string().nullable(), '
                                              'login_username:z.string(), email:z.string().nullable(), '
                                              'contact_person_name:z.string().nullable(), '
                                              'contact_person_designation:z.string().nullable(), '
                                              'contact_phone:z.string().nullable(), '
                                              'address_line1:z.string().nullable(), '
                                              'address_line2:z.string().nullable(), city:z.string().nullable(), '
                                              'state:z.string().nullable(), country:z.string().nullable(), '
                                              'postal_code:z.string().nullable(), status:z.string(), '
                                              'is_active:z.boolean(), created_by:z.number().int().nullable(), '
                                              'created_date:isoDateTimeSchema, updated_by:z.number().int().nullable(), '
                                              'updated_date:nullableDateTime, version:z.number().int().positive() '
                                              '}).strict();\n'
                                              'export const nucleusAccountResponseSchema = z.object({ '
                                              'organization_id:z.string(), account:nucleusAccount, '
                                              'access:accessSchema, generated_at:isoDateTimeSchema }).strict();\n'
                                              'export const nucleusLicenseResponseSchema = z.object({ '
                                              'organization_id:z.string(), license:z.object({ '
                                              'organization_account_id:z.number().int(), '
                                              'max_user_limit:z.number().int().nonnegative(), '
                                              'license_start_date:nullableDateTime, license_end_date:nullableDateTime, '
                                              'is_active:z.boolean(), status:z.string(), '
                                              'version:z.number().int().positive() }).strict(), access:accessSchema, '
                                              'generated_at:isoDateTimeSchema }).strict();\n'
                                              'export const nucleusApprovalStatusResponseSchema = z.object({ '
                                              'organization_id:z.string(), approval:z.object({ '
                                              'organization_account_id:z.number().int(), status:z.string(), '
                                              'approved_by:z.number().int().nullable(), '
                                              'approved_date:nullableDateTime, '
                                              'rejected_by:z.number().int().nullable(), '
                                              'rejected_date:nullableDateTime, rejection_reason:z.string().nullable(), '
                                              'is_active:z.boolean(), version:z.number().int().positive() }).strict(), '
                                              'access:accessSchema, generated_at:isoDateTimeSchema }).strict();\n'
                                              'const entitlementBase = z.object({ access_id:z.number().int(), '
                                              'organization_account_id:z.number().int(), '
                                              'version:z.number().int().positive() });\n'
                                              'export const nucleusEntitlementsResponseSchema = z.object({ '
                                              'organization_id:z.string(), entitlements:z.object({ '
                                              'organization_account_id:z.number().int(), '
                                              'category_access:z.array(entitlementBase.extend({ '
                                              'category_id:z.number().int().nullable(), '
                                              'category_sample_id:z.number().int().nullable(), '
                                              'created_date:nullableDateTime, is_active:z.boolean() }).strict()), '
                                              'company_profile_access:z.array(entitlementBase.extend({ '
                                              'company_id:z.number().int().nullable() }).strict()), '
                                              'drug_access:z.array(entitlementBase.extend({ '
                                              'drug_id:z.number().int().nullable() }).strict()), '
                                              'indication_access:z.array(entitlementBase.extend({ '
                                              'indication_id:z.number().int().nullable() }).strict()), '
                                              'market_access:z.array(entitlementBase.extend({ '
                                              'market_id:z.number().int().nullable(), '
                                              'market_sample_id:z.number().int().nullable() }).strict()), '
                                              'report_access:z.array(entitlementBase.extend({ '
                                              'reports_id:z.number().int().nullable(), '
                                              'sample_id:z.number().int().nullable(), '
                                              'sample_toc_id:z.number().int().nullable(), '
                                              'speciality_id:z.number().int().nullable(), '
                                              'is_executive_access:z.boolean().nullable(), '
                                              'created_date:nullableDateTime, is_active:z.boolean() }).strict()), '
                                              'special_permissions:z.array(z.object({ permission_id:z.number().int(), '
                                              'organization_account_id:z.number().int(), '
                                              'cp_company_master_pharma_id:z.number().int().nullable(), '
                                              'hc_theropetic_category_pharma_id:z.number().int().nullable(), '
                                              'hc_theropetic_category_epidem_id:z.number().int().nullable(), '
                                              'hc_disease_code_epidem_id:z.number().int().nullable(), '
                                              'reports_custom_id:z.number().int().nullable(), '
                                              'importexport_report_id:z.number().int().nullable(), '
                                              'created_date:nullableDateTime, is_active:z.boolean(), '
                                              'version:z.number().int().positive() }).strict()) }).strict(), '
                                              'access:accessSchema, generated_at:isoDateTimeSchema }).strict();\n'
                                              '\n'
                                              'export const workplaceResourceSearchRequestSchema = z.object({ '
                                              'filters:jsonObject.default({}), '
                                              'sort_by:z.string().max(100).nullable().default(null), '
                                              'descending:z.boolean().default(false), '
                                              'limit:z.number().int().min(1).max(100).default(50), '
                                              'offset:z.number().int().nonnegative().default(0) }).strict();\n'
                                              'export const workplaceResourceTypeListResponseSchema = z.object({ '
                                              'resources:z.array(jsonObject) }).strict();\n'
                                              'export const workplaceResourceSchemaResponseSchema = z.object({ '
                                              'resource:jsonObject }).strict();\n'
                                              'export const workplaceResourceSearchResponseSchema = z.object({ '
                                              'items:z.array(jsonObject), total:z.number().int().nonnegative(), '
                                              'limit:z.number().int().min(1).max(100), '
                                              'offset:z.number().int().nonnegative() }).strict();\n'
                                              'export const workplaceResourceCountResponseSchema = z.object({ '
                                              'count:z.number().int().nonnegative() }).strict();\n'
                                              'export const workplaceResourceResponseSchema = z.object({ '
                                              'item:jsonObject }).strict();\n'
                                              '\n'
                                              'export const agentActionNameSchema = z.enum([\n'
                                              "  'update_organization_contact_email',\n"
                                              "  'update_nucleus_organization_account_field',\n"
                                              "  'clear_nucleus_organization_account_field',\n"
                                              "  'grant_nucleus_category_access',\n"
                                              "  'revoke_nucleus_category_access',\n"
                                              "  'grant_nucleus_report_access',\n"
                                              "  'revoke_nucleus_report_access',\n"
                                              "  'update_nucleus_organization_permissions',\n"
                                              "  'update_nucleus_organization_username',\n"
                                              "  'update_nucleus_organization_license',\n"
                                              "  'approve_nucleus_organization_account',\n"
                                              "  'reject_nucleus_organization_account',\n"
                                              "  'activate_nucleus_organization_account',\n"
                                              "  'deactivate_nucleus_organization_account',\n"
                                              "  'grant_nucleus_company_profile_access',\n"
                                              "  'revoke_nucleus_company_profile_access',\n"
                                              "  'grant_nucleus_drug_access',\n"
                                              "  'revoke_nucleus_drug_access',\n"
                                              "  'grant_nucleus_indication_access',\n"
                                              "  'revoke_nucleus_indication_access',\n"
                                              "  'grant_nucleus_market_access',\n"
                                              "  'revoke_nucleus_market_access',\n"
                                              "  'create_workplace_resource',\n"
                                              "  'update_workplace_resource',\n"
                                              "  'clear_workplace_resource_fields',\n"
                                              "  'activate_workplace_resource',\n"
                                              "  'deactivate_workplace_resource',\n"
                                              "  'delete_workplace_resource',\n"
                                              "  'restore_workplace_resource',\n"
                                              "  'bulk_update_workplace_resources',\n"
                                              "  'invite_organization_user',\n"
                                              "  'activate_organization_membership',\n"
                                              "  'update_organization_member_role',\n"
                                              "  'remove_organization_user',\n"
                                              "  'assign_organization_seat',\n"
                                              "  'revoke_organization_seat',\n"
                                              "  'grant_organization_report_access',\n"
                                              "  'revoke_organization_report_access',\n"
                                              "  'bulk_update_workplace_resources_by_query',\n"
                                              "  'onboard_organization_user',\n"
                                              "  'offboard_organization_user',\n"
                                              "  'apply_organization_access_package',\n"
                                              "  'restore_workplace_resource_snapshots'\n"
                                              ']);\n'
                                              'export const actionStatusFilterSchema = '
                                              "z.enum(['pending_approval','approved','rejected','expired','cancelled','stale','executing','succeeded','failed','reconciliation_required']);\n"
                                              'const noArgumentActions = new Set([\n'
                                              "  'approve_nucleus_organization_account',\n"
                                              "  'activate_nucleus_organization_account',\n"
                                              "  'deactivate_nucleus_organization_account'\n"
                                              ']);\n'
                                              'const actionArgumentsSchema = z.record(z.string(), '
                                              'z.string()).superRefine((value, ctx) => {\n'
                                              '  const entries = Object.entries(value);\n'
                                              "  if (entries.length > 12) ctx.addIssue({code:'custom',message:'At most "
                                              "12 action arguments are allowed'});\n"
                                              '  for (const [name, argument] of entries) {\n'
                                              '    if (!name.trim() || name.length > 100 || !argument.trim() || '
                                              'argument.length > 5000) {\n'
                                              "      ctx.addIssue({code:'custom',message:'Action argument names and "
                                              "values must be non-empty and within backend limits'});\n"
                                              '      break;\n'
                                              '    }\n'
                                              '  }\n'
                                              '});\n'
                                              'export const actionProposalRequestSchema = z.object({\n'
                                              '  action_name: agentActionNameSchema,\n'
                                              '  arguments: actionArgumentsSchema.default({}),\n'
                                              '  contact_email: z.email().min(3).max(320).nullable().optional()\n'
                                              '}).strict().superRefine((value, ctx) => {\n'
                                              '  if (value.contact_email !== undefined && value.contact_email !== '
                                              'null) {\n'
                                              "    if (value.action_name !== 'update_organization_contact_email' || "
                                              'Object.keys(value.arguments).length > 0) {\n'
                                              "      ctx.addIssue({code:'custom',message:'contact_email is only valid "
                                              "for update_organization_contact_email'});\n"
                                              '    }\n'
                                              '  } else if (Object.keys(value.arguments).length === 0 && '
                                              '!noArgumentActions.has(value.action_name)) {\n'
                                              "    ctx.addIssue({code:'custom',message:'Action arguments are "
                                              "required'});\n"
                                              '  }\n'
                                              '});\n'
                                              'export const actionDecisionRequestSchema = z.object({ '
                                              'reason:z.string().trim().max(500).nullable().optional() }).strict();\n'
                                              'export const actionExecutionRequestSchema = z.object({ '
                                              'idempotency_key:z.string().trim().min(8).max(200) }).strict();\n'
                                              '\n'
                                              'export const actionChangeSchema = z.object({ field:z.string(), '
                                              'before:z.unknown(), after:z.unknown() }).strict();\n'
                                              'export const approvalPolicySchema = z.object({ '
                                              'self_approval_allowed:z.boolean(), '
                                              'required_approver_permission:z.string(), '
                                              'minimum_approvals:z.number().int().min(1).max(10) }).strict();\n'
                                              'export const actionProposalStatusSchema = '
                                              "z.enum(['pending_approval','approved','rejected','expired','cancelled','stale','executing','succeeded','failed','reconciliation_required']);\n"
                                              'export const actionProposalSchema = z.object({ id:z.string(), '
                                              'organization_id:z.string(), requested_by_user_id:z.string(), '
                                              'action_name:z.string(), arguments:z.record(z.string(),z.string()), '
                                              'action_fingerprint:z.string(), '
                                              'fingerprint_version:z.number().int().min(2).max(4), '
                                              "risk_level:z.enum(['low','medium','high']), resource_type:z.string(), "
                                              'resource_id:z.string(), status:actionProposalStatusSchema, '
                                              'changes:z.array(actionChangeSchema), '
                                              'observed_resource_version:z.number().int().nonnegative(), '
                                              'resource_preconditions:z.array(z.object({resource_type:z.string(),resource_id:z.string(),observed_version:z.number().int().nonnegative()}).strict()), '
                                              'approval_policy:approvalPolicySchema, expires_at:isoDateTimeSchema, '
                                              'cancelled_at:nullableDateTime, stale_at:nullableDateTime, '
                                              'created_at:isoDateTimeSchema }).strict();\n'
                                              'export const actionProposalResponseSchema = z.object({ '
                                              'proposal:actionProposalSchema, requires_approval:z.boolean(), '
                                              'dry_run:z.boolean() }).strict();\n'
                                              'export const actionProposalListResponseSchema = z.object({ '
                                              'proposals:z.array(actionProposalSchema), '
                                              'next_cursor:z.string().nullable() }).strict();\n'
                                              'export const actionApprovalResponseSchema = z.object({ '
                                              'approval:z.object({ proposal_id:z.string(), '
                                              "decision:z.enum(['approved','rejected']), "
                                              'decided_by_user_id:z.string(), decision_reason:z.string().nullable(), '
                                              'decided_at:isoDateTimeSchema, consumed_at:nullableDateTime }).strict() '
                                              '}).strict();\n'
                                              'export const actionExecutionResponseSchema = z.object({ '
                                              'execution:z.object({ proposal_id:z.string(), '
                                              'idempotency_key:z.string(), executed_by_user_id:z.string(), '
                                              'nucleus_actor_id:z.number().int().nullable(), '
                                              "outcome:z.enum(['executing','succeeded','failed','reconciliation_required']), "
                                              'result:jsonObject.nullable(), error_code:z.string().nullable(), '
                                              'attempt_count:z.number().int().positive(), '
                                              'last_attempt_at:nullableDateTime, '
                                              'provider_operation_id:z.string().nullable(), '
                                              'reconciliation_status:z.string().nullable(), audit_pending:z.boolean(), '
                                              'started_at:isoDateTimeSchema, completed_at:nullableDateTime }).strict() '
                                              '}).strict();\n'
                                              'const proposalSummary = z.object({ id:z.string(), '
                                              "action_name:z.string(), risk_level:z.enum(['low','medium','high']), "
                                              "status:z.enum(['pending_approval','approved','rejected','expired','executing','succeeded','failed']), "
                                              'changes:z.array(actionChangeSchema), expires_at:isoDateTimeSchema '
                                              '}).strict();\n'
                                              'export const agentQueryResponseSchema = z.object({ '
                                              "mode:z.enum(['read','action_proposal','clarification_required']), "
                                              'organization_id:z.string(), answer:z.string(), '
                                              'evidence_ids:z.array(z.string()), '
                                              "answer_source:z.enum(['model','deterministic']), "
                                              'results:z.array(z.object({tool_name:z.string(),data:z.unknown()}).strict()), '
                                              'action_proposal:proposalSummary.nullable(), '
                                              'missing_fields:z.array(z.string()) }).strict().superRefine((value, ctx) '
                                              "=> { if (value.mode === 'read' && (value.action_proposal || "
                                              'value.missing_fields.length)) '
                                              "ctx.addIssue({code:'custom',message:'Invalid read response payload'}); "
                                              "if (value.mode === 'action_proposal' && (!value.action_proposal || "
                                              'value.results.length || value.evidence_ids.length || '
                                              'value.missing_fields.length)) '
                                              "ctx.addIssue({code:'custom',message:'Invalid proposal response "
                                              "payload'}); if (value.mode === 'clarification_required' && "
                                              '(value.action_proposal || value.results.length || '
                                              'value.evidence_ids.length || !value.missing_fields.length)) '
                                              "ctx.addIssue({code:'custom',message:'Invalid clarification response "
                                              "payload'}); });\n"
                                              'export const capabilityActionSchema = z.object({ name:z.string(), '
                                              'required_arguments:z.array(z.string()), risk_level:z.string(), '
                                              'requires_approval:z.boolean(), supports_dry_run:z.boolean(), '
                                              'minimum_approvals:z.number().int().positive(), '
                                              'self_approval_allowed:z.boolean(), model_selectable:z.boolean() '
                                              '}).strict();\n'
                                              'export const capabilitiesResponseSchema = z.object({ '
                                              'environment:z.string(), read_tools:z.array(z.string()), '
                                              'write_tools:z.array(z.string()), '
                                              'write_actions:z.array(capabilityActionSchema), '
                                              'approval_required:z.boolean(), production_access:z.boolean() '
                                              '}).strict();\n',
 'frontend/src/app/core/api/workplace-agent-api.service.spec.ts': 'import { provideHttpClient, withInterceptors } from '
                                                                  "'@angular/common/http';\n"
                                                                  'import { provideHttpClientTesting, '
                                                                  'HttpTestingController } from '
                                                                  "'@angular/common/http/testing';\n"
                                                                  "import { TestBed } from '@angular/core/testing';\n"
                                                                  "import { firstValueFrom } from 'rxjs';\n"
                                                                  "import { describe, expect, it } from 'vitest';\n"
                                                                  'import { authHeaderInterceptor } from '
                                                                  "'../auth/auth-header.interceptor';\n"
                                                                  'import { APP_RUNTIME_CONFIG } from '
                                                                  "'../config/app-config.token';\n"
                                                                  'import { WorkplaceAgentApiService } from '
                                                                  "'./workplace-agent-api.service';\n"
                                                                  '\n'
                                                                  "describe('WorkplaceAgentApiService', () => {\n"
                                                                  "  it('uses the canonical query route and auth "
                                                                  "interceptor', async () => {\n"
                                                                  '    TestBed.configureTestingModule({ providers:[\n'
                                                                  '      '
                                                                  "{provide:APP_RUNTIME_CONFIG,useValue:{apiBaseUrl:'http://api.test',defaultOrganizationId:'org_1',mockUserId:'usr_1',requestTimeoutMs:30000,enableDebugViews:false,streamTransport:'rest'}},\n"
                                                                  '      '
                                                                  'provideHttpClient(withInterceptors([authHeaderInterceptor])), '
                                                                  'provideHttpClientTesting()\n'
                                                                  '    ]});\n'
                                                                  '    const '
                                                                  'service=TestBed.inject(WorkplaceAgentApiService); '
                                                                  'const http=TestBed.inject(HttpTestingController);\n'
                                                                  "    const promise=firstValueFrom(service.query('org "
                                                                  "1','  hello  '));\n"
                                                                  '    const '
                                                                  "req=http.expectOne('http://api.test/workplace/organizations/org%201/agent/query');\n"
                                                                  '    '
                                                                  "expect(req.request.headers.get('X-Mock-User-Id')).toBe('usr_1');\n"
                                                                  '    '
                                                                  "expect(req.request.body).toEqual({query:'hello'});\n"
                                                                  "    req.flush({mode:'read',organization_id:'org "
                                                                  "1',answer:'Hello',evidence_ids:[],answer_source:'deterministic',results:[],action_proposal:null,missing_fields:[]});\n"
                                                                  "    expect((await promise).answer).toBe('Hello'); "
                                                                  'http.verify();\n'
                                                                  '  });\n'
                                                                  '});\n',
 'frontend/src/app/core/api/workplace-agent-api.service.ts': "import { HttpParams } from '@angular/common/http';\n"
                                                             "import { inject, Injectable } from '@angular/core';\n"
                                                             "import type { Observable } from 'rxjs';\n"
                                                             'import { ValidatedHttpService } from '
                                                             "'./validated-http.service';\n"
                                                             'import type {\n'
                                                             '  AgentActionApprovalResponse, '
                                                             'AgentActionDecisionRequest, AgentActionExecutionRequest, '
                                                             'AgentActionExecutionResponse,\n'
                                                             '  AgentActionListFilters, '
                                                             'AgentActionProposalListResponse, '
                                                             'AgentActionProposalRequest, AgentActionProposalResponse, '
                                                             'AgentQueryResponse,\n'
                                                             '  AuditLogResponse, CapabilitiesResponse, '
                                                             'HealthResponse, NucleusAccountResponse, '
                                                             'NucleusApprovalStatusResponse,\n'
                                                             '  NucleusEntitlementsResponse, NucleusLicenseResponse, '
                                                             'OrganizationOverviewResponse, '
                                                             'OrganizationProfileResponse,\n'
                                                             '  OrganizationReportsResponse, '
                                                             'OrganizationSeatsResponse, OrganizationUsersResponse, '
                                                             'ReadinessDetailsResponse, ReadinessResponse,\n'
                                                             '  ReportAccessResponse, WorkplaceResourceCountResponse, '
                                                             'WorkplaceResourceResponse, '
                                                             'WorkplaceResourceSchemaResponse,\n'
                                                             '  WorkplaceResourceSearchRequest, '
                                                             'WorkplaceResourceSearchResponse, '
                                                             'WorkplaceResourceTypeListResponse\n'
                                                             "} from './wire.models';\n"
                                                             'import {\n'
                                                             '  actionApprovalResponseSchema, '
                                                             'actionDecisionRequestSchema, '
                                                             'actionExecutionRequestSchema, '
                                                             'actionExecutionResponseSchema, '
                                                             'actionProposalListResponseSchema, '
                                                             'actionProposalRequestSchema, '
                                                             'actionProposalResponseSchema,\n'
                                                             '  agentQueryResponseSchema, auditLogResponseSchema, '
                                                             'capabilitiesResponseSchema, healthSchema, '
                                                             'nucleusAccountResponseSchema,\n'
                                                             '  nucleusApprovalStatusResponseSchema, '
                                                             'nucleusEntitlementsResponseSchema, '
                                                             'nucleusLicenseResponseSchema, '
                                                             'organizationOverviewResponseSchema,\n'
                                                             '  organizationProfileResponseSchema, '
                                                             'organizationReportsResponseSchema, '
                                                             'organizationSeatsResponseSchema, '
                                                             'organizationUsersResponseSchema,\n'
                                                             '  readinessDetailsSchema, readinessSchema, '
                                                             'reportAccessResponseSchema, '
                                                             'workplaceResourceCountResponseSchema, '
                                                             'workplaceResourceResponseSchema,\n'
                                                             '  workplaceResourceSchemaResponseSchema, '
                                                             'workplaceResourceSearchRequestSchema, '
                                                             'workplaceResourceSearchResponseSchema, '
                                                             'workplaceResourceTypeListResponseSchema\n'
                                                             "} from './wire.schemas';\n"
                                                             '\n'
                                                             'function encode(value: string): string { return '
                                                             'encodeURIComponent(value); }\n'
                                                             'function orgPath(organizationId: string): string { '
                                                             'return '
                                                             '`/workplace/organizations/${encode(organizationId)}`; }\n'
                                                             '\n'
                                                             "@Injectable({ providedIn: 'root' })\n"
                                                             'export class WorkplaceAgentApiService {\n'
                                                             '  private readonly client = '
                                                             'inject(ValidatedHttpService);\n'
                                                             '\n'
                                                             '  health(): Observable<HealthResponse> { return '
                                                             "this.client.request('GET','/health',healthSchema); }\n"
                                                             '  readiness(): Observable<ReadinessResponse> { return '
                                                             "this.client.request('GET','/ready',readinessSchema); }\n"
                                                             '  readinessDetails(): '
                                                             'Observable<ReadinessDetailsResponse> { return '
                                                             "this.client.request('GET','/ready/details',readinessDetailsSchema); "
                                                             '}\n'
                                                             '  capabilities(): Observable<CapabilitiesResponse> { '
                                                             'return '
                                                             "this.client.request('GET','/workplace/capabilities',capabilitiesResponseSchema); "
                                                             '}\n'
                                                             '  '
                                                             'organizationOverview(id:string):Observable<OrganizationOverviewResponse>{ '
                                                             'return '
                                                             "this.client.request('GET',`${orgPath(id)}/overview`,organizationOverviewResponseSchema); "
                                                             '}\n'
                                                             '  '
                                                             'organizationProfile(id:string):Observable<OrganizationProfileResponse>{ '
                                                             'return '
                                                             "this.client.request('GET',`${orgPath(id)}/profile`,organizationProfileResponseSchema); "
                                                             '}\n'
                                                             '  '
                                                             'organizationUsers(id:string):Observable<OrganizationUsersResponse>{ '
                                                             'return '
                                                             "this.client.request('GET',`${orgPath(id)}/users`,organizationUsersResponseSchema); "
                                                             '}\n'
                                                             '  '
                                                             'organizationSeats(id:string):Observable<OrganizationSeatsResponse>{ '
                                                             'return '
                                                             "this.client.request('GET',`${orgPath(id)}/seats`,organizationSeatsResponseSchema); "
                                                             '}\n'
                                                             '  '
                                                             'organizationReports(id:string):Observable<OrganizationReportsResponse>{ '
                                                             'return '
                                                             "this.client.request('GET',`${orgPath(id)}/reports`,organizationReportsResponseSchema); "
                                                             '}\n'
                                                             '  '
                                                             'reportAccess(id:string,reportId:string):Observable<ReportAccessResponse>{ '
                                                             'return '
                                                             "this.client.request('GET',`${orgPath(id)}/reports/${encode(reportId)}/access`,reportAccessResponseSchema); "
                                                             '}\n'
                                                             '  auditLog(id:string):Observable<AuditLogResponse>{ '
                                                             'return '
                                                             "this.client.request('GET',`${orgPath(id)}/audit-log`,auditLogResponseSchema); "
                                                             '}\n'
                                                             '  '
                                                             'nucleusAccount(id:string):Observable<NucleusAccountResponse>{ '
                                                             'return '
                                                             "this.client.request('GET',`${orgPath(id)}/nucleus/account`,nucleusAccountResponseSchema); "
                                                             '}\n'
                                                             '  '
                                                             'nucleusLicense(id:string):Observable<NucleusLicenseResponse>{ '
                                                             'return '
                                                             "this.client.request('GET',`${orgPath(id)}/nucleus/license`,nucleusLicenseResponseSchema); "
                                                             '}\n'
                                                             '  '
                                                             'nucleusApprovalStatus(id:string):Observable<NucleusApprovalStatusResponse>{ '
                                                             'return '
                                                             "this.client.request('GET',`${orgPath(id)}/nucleus/approval-status`,nucleusApprovalStatusResponseSchema); "
                                                             '}\n'
                                                             '  '
                                                             'nucleusEntitlements(id:string):Observable<NucleusEntitlementsResponse>{ '
                                                             'return '
                                                             "this.client.request('GET',`${orgPath(id)}/nucleus/entitlements`,nucleusEntitlementsResponseSchema); "
                                                             '}\n'
                                                             '  '
                                                             'resourceTypes(id:string):Observable<WorkplaceResourceTypeListResponse>{ '
                                                             'return '
                                                             "this.client.request('GET',`${orgPath(id)}/resources`,workplaceResourceTypeListResponseSchema); "
                                                             '}\n'
                                                             '  '
                                                             'resourceSchema(id:string,type:string):Observable<WorkplaceResourceSchemaResponse>{ '
                                                             'return '
                                                             "this.client.request('GET',`${orgPath(id)}/resources/${encode(type)}/schema`,workplaceResourceSchemaResponseSchema); "
                                                             '}\n'
                                                             '  '
                                                             'searchResources(id:string,type:string,request:WorkplaceResourceSearchRequest):Observable<WorkplaceResourceSearchResponse>{ '
                                                             'const '
                                                             'body=workplaceResourceSearchRequestSchema.parse(request); '
                                                             'return '
                                                             "this.client.request('POST',`${orgPath(id)}/resources/${encode(type)}/search`,workplaceResourceSearchResponseSchema,{body}); "
                                                             '}\n'
                                                             '  '
                                                             'countResources(id:string,type:string,request:WorkplaceResourceSearchRequest):Observable<WorkplaceResourceCountResponse>{ '
                                                             'const '
                                                             'body=workplaceResourceSearchRequestSchema.parse(request); '
                                                             'return '
                                                             "this.client.request('POST',`${orgPath(id)}/resources/${encode(type)}/count`,workplaceResourceCountResponseSchema,{body}); "
                                                             '}\n'
                                                             '  '
                                                             'resource(id:string,type:string,resourceId:string):Observable<WorkplaceResourceResponse>{ '
                                                             'return '
                                                             "this.client.request('GET',`${orgPath(id)}/resources/${encode(type)}/${encode(resourceId)}`,workplaceResourceResponseSchema); "
                                                             '}\n'
                                                             '  '
                                                             'query(id:string,query:string):Observable<AgentQueryResponse>{ '
                                                             'const normalized=query.trim(); if(!normalized) throw new '
                                                             "Error('Query must not be empty.'); return "
                                                             "this.client.request('POST',`${orgPath(id)}/agent/query`,agentQueryResponseSchema,{body:{query:normalized}}); "
                                                             '}\n'
                                                             '  '
                                                             'propose(id:string,request:AgentActionProposalRequest):Observable<AgentActionProposalResponse>{ '
                                                             'const body=actionProposalRequestSchema.parse(request); '
                                                             'return '
                                                             "this.client.request('POST',`${orgPath(id)}/agent/actions/propose`,actionProposalResponseSchema,{body}); "
                                                             '}\n'
                                                             '  '
                                                             'listProposals(id:string,filters:AgentActionListFilters={}):Observable<AgentActionProposalListResponse>{ '
                                                             'let params=new HttpParams(); '
                                                             "if(filters.status)params=params.set('status',filters.status); "
                                                             "if(filters.actionName)params=params.set('action_name',filters.actionName); "
                                                             "if(filters.requestedBy)params=params.set('requested_by',filters.requestedBy); "
                                                             "if(filters.limit)params=params.set('limit',String(filters.limit)); "
                                                             "if(filters.cursor)params=params.set('cursor',filters.cursor); "
                                                             'return '
                                                             "this.client.request('GET',`${orgPath(id)}/agent/actions`,actionProposalListResponseSchema,{params}); "
                                                             '}\n'
                                                             '  '
                                                             'proposal(id:string,proposalId:string):Observable<AgentActionProposalResponse>{ '
                                                             'return '
                                                             "this.client.request('GET',`${orgPath(id)}/agent/actions/${encode(proposalId)}`,actionProposalResponseSchema); "
                                                             '}\n'
                                                             '  '
                                                             'approve(id:string,proposalId:string,request:AgentActionDecisionRequest={}):Observable<AgentActionApprovalResponse>{ '
                                                             "return this.decision(id,proposalId,'approve',request); "
                                                             '}\n'
                                                             '  '
                                                             'reject(id:string,proposalId:string,request:AgentActionDecisionRequest={}):Observable<AgentActionApprovalResponse>{ '
                                                             "return this.decision(id,proposalId,'reject',request); }\n"
                                                             '  '
                                                             'cancel(id:string,proposalId:string,request:AgentActionDecisionRequest={}):Observable<AgentActionProposalResponse>{ '
                                                             'const body=actionDecisionRequestSchema.parse(request); '
                                                             'return '
                                                             "this.client.request('POST',`${orgPath(id)}/agent/actions/${encode(proposalId)}/cancel`,actionProposalResponseSchema,{body}); "
                                                             '}\n'
                                                             '  '
                                                             'createRollbackProposal(id:string,proposalId:string,request:AgentActionDecisionRequest={}):Observable<AgentActionProposalResponse>{ '
                                                             'const body=actionDecisionRequestSchema.parse(request); '
                                                             'return '
                                                             "this.client.request('POST',`${orgPath(id)}/agent/actions/${encode(proposalId)}/rollback-proposal`,actionProposalResponseSchema,{body}); "
                                                             '}\n'
                                                             '  '
                                                             'execute(id:string,proposalId:string,request:AgentActionExecutionRequest):Observable<AgentActionExecutionResponse>{ '
                                                             'const body=actionExecutionRequestSchema.parse(request); '
                                                             'return '
                                                             "this.client.request('POST',`${orgPath(id)}/agent/actions/${encode(proposalId)}/execute`,actionExecutionResponseSchema,{body}); "
                                                             '}\n'
                                                             '  '
                                                             'reconcile(id:string,proposalId:string):Observable<AgentActionExecutionResponse>{ '
                                                             'return '
                                                             "this.client.request('POST',`${orgPath(id)}/agent/actions/${encode(proposalId)}/reconcile`,actionExecutionResponseSchema); "
                                                             '}\n'
                                                             '  '
                                                             'replayAudit(id:string,proposalId:string):Observable<AgentActionExecutionResponse>{ '
                                                             'return '
                                                             "this.client.request('POST',`${orgPath(id)}/agent/actions/${encode(proposalId)}/audit-replay`,actionExecutionResponseSchema); "
                                                             '}\n'
                                                             '  private '
                                                             "decision(id:string,proposalId:string,kind:'approve'|'reject',request:AgentActionDecisionRequest):Observable<AgentActionApprovalResponse>{ "
                                                             'const body=actionDecisionRequestSchema.parse(request); '
                                                             'return '
                                                             "this.client.request('POST',`${orgPath(id)}/agent/actions/${encode(proposalId)}/${kind}`,actionApprovalResponseSchema,{body}); "
                                                             '}\n'
                                                             '}\n',
 'frontend/src/app/core/auth/auth-header.interceptor.ts': 'import type { HttpInterceptorFn } from '
                                                          "'@angular/common/http';\n"
                                                          "import { inject } from '@angular/core';\n"
                                                          'import { APP_RUNTIME_CONFIG } from '
                                                          "'../config/app-config.token';\n"
                                                          "import { CurrentUserStore } from './current-user.store';\n"
                                                          '\n'
                                                          'export const authHeaderInterceptor: HttpInterceptorFn = '
                                                          '(request, next) => {\n'
                                                          '  const config = inject(APP_RUNTIME_CONFIG);\n'
                                                          '  const userId = inject(CurrentUserStore).userId();\n'
                                                          '  if (!userId || '
                                                          '!request.url.startsWith(config.apiBaseUrl)) {\n'
                                                          '    return next(request);\n'
                                                          '  }\n'
                                                          '  return next(request.clone({ setHeaders: { '
                                                          "'X-Mock-User-Id': userId } }));\n"
                                                          '};\n',
 'frontend/src/app/core/auth/current-user.store.ts': 'import { computed, inject, Injectable, signal } from '
                                                     "'@angular/core';\n"
                                                     'import { APP_RUNTIME_CONFIG } from '
                                                     "'../config/app-config.token';\n"
                                                     '\n'
                                                     "@Injectable({ providedIn: 'root' })\n"
                                                     'export class CurrentUserStore {\n'
                                                     '  private readonly configuredUserId = '
                                                     'inject(APP_RUNTIME_CONFIG).mockUserId;\n'
                                                     '  private readonly userIdState = signal<string | '
                                                     'null>(this.configuredUserId);\n'
                                                     '  readonly userId = this.userIdState.asReadonly();\n'
                                                     '  readonly isAuthenticated = computed(() => this.userId() !== '
                                                     'null);\n'
                                                     '\n'
                                                     '  setSandboxUser(userId: string | null): void {\n'
                                                     '    const normalized = userId?.trim() ?? null;\n'
                                                     '    this.userIdState.set(normalized || null);\n'
                                                     '  }\n'
                                                     '}\n',
 'frontend/src/app/core/config/app-config.loader.spec.ts': "import { describe, expect, it, vi } from 'vitest';\n"
                                                           'import { loadAppRuntimeConfig } from '
                                                           "'./app-config.loader';\n"
                                                           '\n'
                                                           "describe('loadAppRuntimeConfig', () => {\n"
                                                           "  it('loads and normalizes a valid configuration', async "
                                                           '() => {\n'
                                                           '    const fetcher = vi.fn<typeof '
                                                           'fetch>().mockResolvedValue(new Response(JSON.stringify({ '
                                                           "apiBaseUrl:'http://127.0.0.1:8000/', "
                                                           "defaultOrganizationId:'org_1', mockUserId:'usr_1', "
                                                           'requestTimeoutMs:30000, enableDebugViews:false, '
                                                           "streamTransport:'rest' }), {status:200, "
                                                           "headers:{'content-type':'application/json'}}));\n"
                                                           '    const result = await '
                                                           "loadAppRuntimeConfig('/config/app-config.json', fetcher);\n"
                                                           '    '
                                                           "expect(result.apiBaseUrl).toBe('http://127.0.0.1:8000');\n"
                                                           '  });\n'
                                                           "  it('rejects unknown fields', async () => {\n"
                                                           '    const fetcher = vi.fn<typeof '
                                                           'fetch>().mockResolvedValue(new Response(JSON.stringify({ '
                                                           "apiBaseUrl:'http://127.0.0.1:8000', "
                                                           'defaultOrganizationId:null, mockUserId:null, '
                                                           'requestTimeoutMs:30000, enableDebugViews:false, '
                                                           "streamTransport:'rest', unexpected:true }), "
                                                           '{status:200}));\n'
                                                           '    await '
                                                           "expect(loadAppRuntimeConfig('/config/app-config.json', "
                                                           'fetcher)).rejects.toThrow();\n'
                                                           '  });\n'
                                                           '});\n',
 'frontend/src/app/core/config/app-config.loader.ts': 'import { appRuntimeConfigSchema, type AppRuntimeConfig } from '
                                                      "'./app-config.model';\n"
                                                      '\n'
                                                      'export async function loadAppRuntimeConfig(url: string, '
                                                      'fetcher: typeof fetch = fetch): Promise<AppRuntimeConfig> {\n'
                                                      "  const response = await fetcher(url, { cache: 'no-store', "
                                                      "credentials: 'same-origin' });\n"
                                                      '  if (!response.ok) {\n'
                                                      '    throw new Error(`Runtime configuration request failed with '
                                                      'status ${response.status}.`);\n'
                                                      '  }\n'
                                                      '  const payload: unknown = await response.json();\n'
                                                      '  return appRuntimeConfigSchema.parse(payload);\n'
                                                      '}\n',
 'frontend/src/app/core/config/app-config.model.ts': "import { z } from 'zod';\n"
                                                     '\n'
                                                     'export const appRuntimeConfigSchema = z.object({\n'
                                                     '  apiBaseUrl: z.url().transform((value) => value.replace(/\\/$/, '
                                                     "'')),\n"
                                                     '  defaultOrganizationId: z.string().trim().min(1).nullable(),\n'
                                                     '  mockUserId: z.string().trim().min(1).nullable(),\n'
                                                     '  requestTimeoutMs: z.number().int().min(1000).max(120000),\n'
                                                     '  enableDebugViews: z.boolean(),\n'
                                                     "  streamTransport: z.literal('rest')\n"
                                                     '}).strict();\n'
                                                     '\n'
                                                     'export type AppRuntimeConfig = z.infer<typeof '
                                                     'appRuntimeConfigSchema>;\n',
 'frontend/src/app/core/config/app-config.token.ts': "import { InjectionToken } from '@angular/core';\n"
                                                     "import type { AppRuntimeConfig } from './app-config.model';\n"
                                                     '\n'
                                                     'export const APP_RUNTIME_CONFIG = new '
                                                     "InjectionToken<AppRuntimeConfig>('APP_RUNTIME_CONFIG');\n",
 'frontend/src/app/core/errors/error-normalizer.spec.ts': "import { describe, expect, it } from 'vitest';\n"
                                                          'import { normalizeWorkplaceError } from '
                                                          "'./error-normalizer';\n"
                                                          "import { WorkplaceApiError } from './workplace-api.error';\n"
                                                          '\n'
                                                          "describe('normalizeWorkplaceError', () => {\n"
                                                          "  it('maps stale proposals to a new-proposal action', () => "
                                                          '{\n'
                                                          '    const view = normalizeWorkplaceError(new '
                                                          "WorkplaceApiError(409,'agent_action_stale','State "
                                                          "changed','req_1'));\n"
                                                          '    '
                                                          "expect(view.suggestedAction).toBe('request_new_proposal');\n"
                                                          "    expect(view.requestId).toBe('req_1');\n"
                                                          '  });\n'
                                                          '});\n',
 'frontend/src/app/core/errors/error-normalizer.ts': 'import type { WorkplaceErrorView } from '
                                                     "'./workplace-api.error';\n"
                                                     "import { WorkplaceApiError } from './workplace-api.error';\n"
                                                     '\n'
                                                     "const STALE_CODES = new Set(['agent_action_expired', "
                                                     "'agent_action_stale', 'agent_action_cancelled']);\n"
                                                     "const RETRYABLE_CODES = new Set(['agent_model_request_failed', "
                                                     "'agent_model_unavailable', 'internal_error']);\n"
                                                     '\n'
                                                     'export function normalizeWorkplaceError(error: unknown): '
                                                     'WorkplaceErrorView {\n'
                                                     '  if (!(error instanceof WorkplaceApiError)) {\n'
                                                     "    return { code: 'unknown_error', title: 'Something went "
                                                     "wrong', message: 'The request could not be completed.', "
                                                     "retryable: false, suggestedAction: 'contact_admin' };\n"
                                                     '  }\n'
                                                     '  if (STALE_CODES.has(error.code)) {\n'
                                                     "    return { code: error.code, title: 'Proposal is no longer "
                                                     "current', message: error.message, requestId: error.requestId, "
                                                     "retryable: false, suggestedAction: 'request_new_proposal' };\n"
                                                     '  }\n'
                                                     "  if (error.code === 'permission_denied' || error.code === "
                                                     "'organization_access_denied') {\n"
                                                     "    return { code: error.code, title: 'Access denied', message: "
                                                     'error.message, requestId: error.requestId, retryable: false, '
                                                     "suggestedAction: 'contact_admin' };\n"
                                                     '  }\n'
                                                     '  const retryable = RETRYABLE_CODES.has(error.code) || '
                                                     'error.status === 0 || error.status >= 500;\n'
                                                     "  return { code: error.code, title: retryable ? 'Service "
                                                     "temporarily unavailable' : 'Request could not be completed', "
                                                     'message: error.message, requestId: error.requestId, retryable, '
                                                     "suggestedAction: retryable ? 'retry' : 'none' };\n"
                                                     '}\n',
 'frontend/src/app/core/errors/workplace-api.error.ts': 'export interface WorkplaceErrorView {\n'
                                                        '  code: string;\n'
                                                        '  title: string;\n'
                                                        '  message: string;\n'
                                                        '  requestId?: string;\n'
                                                        '  retryable: boolean;\n'
                                                        "  suggestedAction: 'retry' | 'refresh' | "
                                                        "'request_new_proposal' | 'contact_admin' | 'none';\n"
                                                        '}\n'
                                                        '\n'
                                                        'export class WorkplaceApiError extends Error {\n'
                                                        '  constructor(\n'
                                                        '    readonly status: number,\n'
                                                        '    readonly code: string,\n'
                                                        '    message: string,\n'
                                                        '    readonly requestId?: string,\n'
                                                        '    readonly causeValue?: unknown\n'
                                                        '  ) {\n'
                                                        '    super(message, { cause: causeValue });\n'
                                                        "    this.name = 'WorkplaceApiError';\n"
                                                        '  }\n'
                                                        '}\n',
 'frontend/src/index.html': '<!doctype html>\n'
                            '<html lang="en">\n'
                            '  <head>\n'
                            '    <meta charset="utf-8">\n'
                            '    <title>DBMR Workplace Agent</title>\n'
                            '    <base href="/">\n'
                            '    <meta name="viewport" content="width=device-width, initial-scale=1">\n'
                            '    <meta name="color-scheme" content="light dark">\n'
                            '    <meta name="description" content="Governed workplace-agent interface">\n'
                            '  </head>\n'
                            '  <body>\n'
                            '    <app-root></app-root>\n'
                            '    <noscript>This application requires JavaScript.</noscript>\n'
                            '  </body>\n'
                            '</html>\n',
 'frontend/src/main.ts': "import { bootstrapApplication } from '@angular/platform-browser';\n"
                         "import { AppComponent } from './app/app.component';\n"
                         "import { createAppConfig } from './app/app.config';\n"
                         "import { loadAppRuntimeConfig } from './app/core/config/app-config.loader';\n"
                         '\n'
                         'async function start(): Promise<void> {\n'
                         "  const runtimeConfig = await loadAppRuntimeConfig('/config/app-config.json');\n"
                         '  await bootstrapApplication(AppComponent, createAppConfig(runtimeConfig));\n'
                         '}\n'
                         '\n'
                         'void start().catch((error: unknown) => {\n'
                         "  console.error('Angular bootstrap failed', error);\n"
                         "  const root = document.querySelector('app-root');\n"
                         '  if (root) {\n'
                         "    const message = document.createElement('main');\n"
                         "    message.setAttribute('role', 'alert');\n"
                         "    message.style.cssText = 'padding:24px;font-family:system-ui';\n"
                         "    message.textContent = 'The application could not start because its runtime configuration "
                         "is invalid.';\n"
                         '    root.replaceChildren(message);\n'
                         '  }\n'
                         '});\n',
 'frontend/src/styles.scss': ':root {\n'
                             '  color-scheme: light;\n'
                             '  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, '
                             '"Segoe UI", sans-serif;\n'
                             '  background: #f5f5f6;\n'
                             '  color: #171717;\n'
                             '}\n'
                             '\n'
                             '* { box-sizing: border-box; }\n'
                             'html, body { min-height: 100%; margin: 0; }\n'
                             'body { min-width: 320px; }\n'
                             'button, input, textarea, select { font: inherit; }\n'
                             ':focus-visible { outline: 2px solid #2563eb; outline-offset: 2px; }\n'
                             '.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; '
                             'overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }\n'
                             '\n'
                             '@media (prefers-reduced-motion: reduce) {\n'
                             '  *, *::before, *::after { scroll-behavior: auto !important; animation-duration: 0.01ms '
                             '!important; animation-iteration-count: 1 !important; transition-duration: 0.01ms '
                             '!important; }\n'
                             '}\n',
 'frontend/tsconfig.app.json': '{\n'
                               '  "extends": "./tsconfig.json",\n'
                               '  "compilerOptions": {\n'
                               '    "outDir": "./out-tsc/app",\n'
                               '    "types": []\n'
                               '  },\n'
                               '  "files": [\n'
                               '    "src/main.ts"\n'
                               '  ],\n'
                               '  "include": [\n'
                               '    "src/**/*.d.ts"\n'
                               '  ]\n'
                               '}\n',
 'frontend/tsconfig.e2e.json': '{\n'
                               '  "extends": "./tsconfig.json",\n'
                               '  "compilerOptions": {\n'
                               '    "outDir": "./out-tsc/e2e",\n'
                               '    "types": [\n'
                               '      "node"\n'
                               '    ]\n'
                               '  },\n'
                               '  "include": [\n'
                               '    "e2e/**/*.ts",\n'
                               '    "playwright.config.ts"\n'
                               '  ]\n'
                               '}\n',
 'frontend/tsconfig.json': '{\n'
                           '  "compileOnSave": false,\n'
                           '  "compilerOptions": {\n'
                           '    "baseUrl": "./",\n'
                           '    "outDir": "./dist/out-tsc",\n'
                           '    "forceConsistentCasingInFileNames": true,\n'
                           '    "strict": true,\n'
                           '    "noImplicitOverride": true,\n'
                           '    "noPropertyAccessFromIndexSignature": true,\n'
                           '    "noImplicitReturns": true,\n'
                           '    "noFallthroughCasesInSwitch": true,\n'
                           '    "sourceMap": true,\n'
                           '    "declaration": false,\n'
                           '    "downlevelIteration": true,\n'
                           '    "experimentalDecorators": true,\n'
                           '    "moduleResolution": "bundler",\n'
                           '    "importHelpers": true,\n'
                           '    "target": "ES2022",\n'
                           '    "module": "ES2022",\n'
                           '    "useDefineForClassFields": false,\n'
                           '    "lib": [\n'
                           '      "ES2022",\n'
                           '      "dom",\n'
                           '      "dom.iterable"\n'
                           '    ],\n'
                           '    "types": [],\n'
                           '    "skipLibCheck": true\n'
                           '  },\n'
                           '  "angularCompilerOptions": {\n'
                           '    "enableI18nLegacyMessageIdFormat": false,\n'
                           '    "strictInjectionParameters": true,\n'
                           '    "strictInputAccessModifiers": true,\n'
                           '    "strictTemplates": true\n'
                           '  }\n'
                           '}\n',
 'frontend/tsconfig.spec.json': '{\n'
                                '  "extends": "./tsconfig.json",\n'
                                '  "compilerOptions": {\n'
                                '    "outDir": "./out-tsc/spec",\n'
                                '    "types": ["vitest/globals", "node"]\n'
                                '  },\n'
                                '  "include": ["src/**/*.spec.ts", "src/**/*.d.ts"]\n'
                                '}\n',
 'scripts/validate_angular_phase1.py': '#!/usr/bin/env python3\n'
                                       '"""Static, dependency-free validation for the Angular Phase 1 foundation."""\n'
                                       'from __future__ import annotations\n'
                                       '\n'
                                       'import argparse\n'
                                       'import json\n'
                                       'import re\n'
                                       'import subprocess\n'
                                       'from pathlib import Path\n'
                                       '\n'
                                       'EXPECTED_PACKAGES = {\n'
                                       '    "@angular/core": "21.2.18",\n'
                                       '    "@angular/common": "21.2.18",\n'
                                       '    "@angular/compiler": "21.2.18",\n'
                                       '    "@angular/platform-browser": "21.2.18",\n'
                                       '    "@angular/router": "21.2.18",\n'
                                       '    "@angular/cdk": "21.2.14",\n'
                                       '    "zod": "4.4.3",\n'
                                       '    "@angular/cli": "21.2.18",\n'
                                       '    "@angular/build": "21.2.18",\n'
                                       '    "typescript": "5.9.3",\n'
                                       '    "vitest": "4.1.10",\n'
                                       '    "@playwright/test": "1.61.1",\n'
                                       '}\n'
                                       '\n'
                                       'REQUIRED_FILES = (\n'
                                       '    "frontend/package.json",\n'
                                       '    "frontend/angular.json",\n'
                                       '    "frontend/tsconfig.json",\n'
                                       '    "frontend/tsconfig.app.json",\n'
                                       '    "frontend/tsconfig.spec.json",\n'
                                       '    "frontend/tsconfig.e2e.json",\n'
                                       '    "frontend/eslint.config.mjs",\n'
                                       '    "frontend/playwright.config.ts",\n'
                                       '    "frontend/public/config/app-config.json",\n'
                                       '    "frontend/src/main.ts",\n'
                                       '    "frontend/src/app/app.config.ts",\n'
                                       '    "frontend/src/app/core/config/app-config.model.ts",\n'
                                       '    "frontend/src/app/core/api/wire.schemas.ts",\n'
                                       '    "frontend/src/app/core/api/workplace-agent-api.service.ts",\n'
                                       '    "frontend/src/app/core/api/validated-http.service.ts",\n'
                                       '    "frontend/src/app/core/api/api-error.interceptor.ts",\n'
                                       '    "frontend/src/app/core/auth/auth-header.interceptor.ts",\n'
                                       '    "frontend/src/app/core/errors/error-normalizer.ts",\n'
                                       '    "frontend/e2e/foundation.spec.ts",\n'
                                       '    "frontend/docs/PHASE_1_ARCHITECTURE.md",\n'
                                       '    "frontend/docs/PHASE_1_ACCEPTANCE.md",\n'
                                       ')\n'
                                       '\n'
                                       'ROUTE_TOKENS = (\n'
                                       '    "/health", "/ready", "/ready/details", "/workplace/capabilities",\n'
                                       '    "/overview", "/profile", "/users", "/seats", "/reports", "/access",\n'
                                       '    "/audit-log", "/nucleus/account", "/nucleus/license", '
                                       '"/nucleus/approval-status",\n'
                                       '    "/nucleus/entitlements", "/resources", "/schema", "/search", "/count",\n'
                                       '    "/agent/query", "/agent/actions/propose", "/agent/actions",\n'
                                       '    "/cancel", "/rollback-proposal", "/execute", "/reconcile", '
                                       '"/audit-replay",\n'
                                       ')\n'
                                       '\n'
                                       '\n'
                                       'def validate(repo: Path) -> None:\n'
                                       '    frontend = repo / "frontend"\n'
                                       '    phase0_manifest = frontend / "contracts/api-manifest.json"\n'
                                       '    if not phase0_manifest.is_file():\n'
                                       '        raise RuntimeError("Phase 0 contract manifest is missing.")\n'
                                       '    manifest = json.loads(phase0_manifest.read_text(encoding="utf-8"))\n'
                                       '    endpoints = manifest.get("endpoints")\n'
                                       '    if not isinstance(endpoints, list) or len(endpoints) != 31:\n'
                                       '        raise RuntimeError("Phase 0 must expose exactly 31 endpoint '
                                       'contracts.")\n'
                                       '\n'
                                       '    for relative in REQUIRED_FILES:\n'
                                       '        if not (repo / relative).is_file():\n'
                                       '            raise RuntimeError(f"Missing Phase 1 file: {relative}")\n'
                                       '\n'
                                       '    package = json.loads((frontend / '
                                       '"package.json").read_text(encoding="utf-8"))\n'
                                       '    combined = {**package.get("dependencies", {}), '
                                       '**package.get("devDependencies", {})}\n'
                                       '    for name, version in EXPECTED_PACKAGES.items():\n'
                                       '        if combined.get(name) != version:\n'
                                       '            raise RuntimeError(f"Unexpected package pin for {name}: '
                                       '{combined.get(name)!r}")\n'
                                       '    scripts = package.get("scripts", {})\n'
                                       '    for name in ("typecheck", "lint", "test", "build", "e2e", '
                                       '"validate:phase1"):\n'
                                       '        if name not in scripts:\n'
                                       '            raise RuntimeError(f"Missing npm script: {name}")\n'
                                       '\n'
                                       '    angular = json.loads((frontend / '
                                       '"angular.json").read_text(encoding="utf-8"))\n'
                                       '    project = angular["projects"]["workplace-agent-ui"]\n'
                                       '    if project["architect"]["build"]["builder"] != '
                                       '"@angular/build:application":\n'
                                       '        raise RuntimeError("Angular application builder is not configured.")\n'
                                       '    if project["architect"]["test"]["builder"] != "@angular/build:unit-test":\n'
                                       '        raise RuntimeError("Angular Vitest unit-test builder is not '
                                       'configured.")\n'
                                       '\n'
                                       '    runtime_config = json.loads((frontend / '
                                       '"public/config/app-config.json").read_text(encoding="utf-8"))\n'
                                       '    if runtime_config.get("streamTransport") != "rest":\n'
                                       '        raise RuntimeError("Phase 1 must not claim that streaming exists.")\n'
                                       '\n'
                                       '    api_text = (frontend / '
                                       '"src/app/core/api/workplace-agent-api.service.ts").read_text(encoding="utf-8")\n'
                                       '    for token in ROUTE_TOKENS:\n'
                                       '        if token not in api_text:\n'
                                       '            raise RuntimeError(f"API facade route token missing: {token}")\n'
                                       '    if len(re.findall(r"Observable<", api_text)) < 31:\n'
                                       '        raise RuntimeError("API facade does not expose all 31 typed '
                                       'operations.")\n'
                                       '    if "approve(id:string" not in api_text or "reject(id:string" not in '
                                       'api_text:\n'
                                       '        raise RuntimeError("Approval decision methods are missing.")\n'
                                       '\n'
                                       '    all_typescript = "\\n".join(\n'
                                       '        path.read_text(encoding="utf-8")\n'
                                       '        for path in (frontend / "src/app").rglob("*.ts")\n'
                                       '        if not path.name.endswith(".spec.ts")\n'
                                       '    )\n'
                                       '    if re.search(r"(:\\s*any\\b|<any>)", all_typescript):\n'
                                       '        raise RuntimeError("Explicit any is forbidden in Phase 1 source.")\n'
                                       '    if "new EventSource" in all_typescript or "new WebSocket" in '
                                       'all_typescript:\n'
                                       '        raise RuntimeError("Phase 1 must not invent a streaming transport.")\n'
                                       '\n'
                                       '    boundary = subprocess.run(\n'
                                       '        ["node", "scripts/check-architecture-boundaries.mjs"],\n'
                                       '        cwd=frontend,\n'
                                       '        text=True,\n'
                                       '        stdout=subprocess.PIPE,\n'
                                       '        stderr=subprocess.STDOUT,\n'
                                       '        check=False,\n'
                                       '    )\n'
                                       '    if boundary.returncode != 0:\n'
                                       '        raise RuntimeError(boundary.stdout)\n'
                                       '\n'
                                       '\n'
                                       'def main() -> int:\n'
                                       '    parser = argparse.ArgumentParser()\n'
                                       '    parser.add_argument("--repo", default=".")\n'
                                       '    args = parser.parse_args()\n'
                                       '    repo = Path(args.repo).resolve()\n'
                                       '    validate(repo)\n'
                                       '    print("Angular Phase 1 foundation is valid: 31 typed API operations, '
                                       'strict runtime boundaries, and no fake streaming.")\n'
                                       '    return 0\n'
                                       '\n'
                                       '\n'
                                       'if __name__ == "__main__":\n'
                                       '    raise SystemExit(main())\n',
 'tests/test_angular_phase1_foundation.py': 'from __future__ import annotations\n'
                                            '\n'
                                            'import importlib.util\n'
                                            'from pathlib import Path\n'
                                            '\n'
                                            '\n'
                                            'def _validator_module():\n'
                                            '    root = Path(__file__).resolve().parents[1]\n'
                                            '    path = root / "scripts" / "validate_angular_phase1.py"\n'
                                            '    spec = '
                                            'importlib.util.spec_from_file_location("validate_angular_phase1", path)\n'
                                            '    assert spec is not None and spec.loader is not None\n'
                                            '    module = importlib.util.module_from_spec(spec)\n'
                                            '    spec.loader.exec_module(module)\n'
                                            '    return module\n'
                                            '\n'
                                            '\n'
                                            'def test_angular_phase1_static_contract() -> None:\n'
                                            '    root = Path(__file__).resolve().parents[1]\n'
                                            '    _validator_module().validate(root)\n'
                                            '\n'
                                            '\n'
                                            'def test_frontend_does_not_claim_streaming_exists() -> None:\n'
                                            '    root = Path(__file__).resolve().parents[1]\n'
                                            '    config = (root / '
                                            '"frontend/public/config/app-config.json").read_text(encoding="utf-8")\n'
                                            '    source = "\\n".join(\n'
                                            '        path.read_text(encoding="utf-8")\n'
                                            '        for path in (root / "frontend/src/app").rglob("*.ts")\n'
                                            '    )\n'
                                            '    assert \'"streamTransport": "rest"\' in config\n'
                                            '    assert "new EventSource" not in source\n'
                                            '    assert "new WebSocket" not in source\n'}

APPENDS = {'APPLY_AND_VALIDATE.md': '\n'
                          '\n'
                          '<!-- ANGULAR_FRONTEND_PHASE_1_VALIDATION -->\n'
                          '## Angular frontend Phase 1 validation\n'
                          '\n'
                          '```powershell\n'
                          'python scripts/validate_frontend_contracts.py --repo .\n'
                          'python scripts/validate_angular_phase1.py --repo .\n'
                          'pytest -q tests/test_frontend_contracts.py tests/test_angular_phase1_foundation.py\n'
                          '\n'
                          'Set-Location frontend\n'
                          'npm install\n'
                          'npm run validate:phase1\n'
                          'npx playwright install chromium\n'
                          'npm run e2e\n'
                          'Set-Location ..\n'
                          '\n'
                          'pytest -q\n'
                          'git diff --check\n'
                          'git status --short\n'
                          '```\n'
                          '\n'
                          'Expected frontend foundation: Angular 21 LTS, strict standalone/zoneless\n'
                          'bootstrap, 31 typed API operations, functional interceptors, fail-closed runtime\n'
                          'validation, Vitest tests and Playwright discovery. Streaming remains unavailable\n'
                          'and must not be simulated.\n',
 'README.md': '\n'
              '\n'
              '<!-- ANGULAR_FRONTEND_PHASE_1_FOUNDATION -->\n'
              '## Angular frontend Phase 1\n'
              '\n'
              'The governed backend now has a native Angular 21 LTS frontend foundation under\n'
              '`frontend/`. All 31 existing backend operations are hidden behind one validated\n'
              'Angular API facade. Phase 1 adds no fake streaming, reasoning, proposal progress\n'
              'or execution progress.\n'
              '\n'
              'Validate with:\n'
              '\n'
              '```bash\n'
              'python scripts/validate_angular_phase1.py --repo .\n'
              'pytest -q tests/test_angular_phase1_foundation.py\n'
              'cd frontend\n'
              'npm run validate:phase1\n'
              '```\n',
 'frontend/README.md': '\n'
                       '\n'
                       '<!-- ANGULAR_FRONTEND_PHASE_1_FOUNDATION -->\n'
                       '## Phase 1 Angular foundation\n'
                       '\n'
                       'The repository now contains a strict Angular 21 LTS application, a runtime\n'
                       'configuration bootstrap, functional request/auth/error interceptors, Zod\n'
                       'validation for the current backend wire contracts, and a single typed facade\n'
                       'covering all 31 Phase 0 endpoint method/path pairs.\n'
                       '\n'
                       '```bash\n'
                       'cd frontend\n'
                       'npm install\n'
                       'npm run validate:phase1\n'
                       'npx playwright install chromium\n'
                       'npm run e2e\n'
                       '```\n'
                       '\n'
                       'The current shell is intentionally structural. Cloudflare-style visual tokens\n'
                       'and reusable controls are implemented in Phase 2; full dashboard and Ask AI\n'
                       'experiences follow in later phases.\n',
 'frontend/docs/PHASE_0_GAPS.md': '\n'
                                  '\n'
                                  '<!-- ANGULAR_FRONTEND_PHASE_1_STATUS -->\n'
                                  '## Status after Phase 1\n'
                                  '\n'
                                  'Phase 1 closes the missing Angular runtime, runtime configuration, typed API\n'
                                  'facade, request correlation, sandbox-auth interceptor, runtime response\n'
                                  'validation, unit-test foundation and Playwright foundation.\n'
                                  '\n'
                                  'Conversation persistence, SSE/WebSocket streaming, backend activity events,\n'
                                  'execution-step projections, file upload and request-changes behavior remain\n'
                                  'unimplemented. The Angular application explicitly uses `streamTransport: rest`\n'
                                  'and does not simulate any of those capabilities.\n'}


def run(repo: Path, *args: str, check: bool = True, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd or repo,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def git(repo: Path, *args: str, check: bool = True) -> str:
    return run(repo, "git", *args, check=check).stdout.strip()


def normalized_origin(value: str) -> str:
    return value.removesuffix(".git").replace("git@github.com:", "https://github.com/")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_node(repo: Path) -> None:
    node = run(repo, "node", "--version", check=False)
    npm = run(repo, NPM, "--version", check=False)
    if node.returncode != 0 or npm.returncode != 0:
        raise RuntimeError("Node.js and npm are required for Angular Phase 1.")
    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", node.stdout.strip())
    if match is None:
        raise RuntimeError(f"Could not parse Node.js version: {node.stdout.strip()}")
    major, minor, _patch = (int(value) for value in match.groups())
    supported = (
        (major == 20 and minor >= 19)
        or (major == 22 and minor >= 12)
        or major == 24
    )
    if not supported:
        raise RuntimeError(
            "Angular 21 requires Node.js ^20.19.0, ^22.12.0, or ^24.0.0; "
            f"found {node.stdout.strip()}."
        )


def verify_repo(repo: Path) -> None:
    root = Path(git(repo, "rev-parse", "--show-toplevel")).resolve()
    if root != repo:
        raise RuntimeError("Run from the repository root or pass --repo.")
    branch = git(repo, "branch", "--show-current")
    if branch != EXPECTED_BRANCH:
        raise RuntimeError(f"Expected branch {EXPECTED_BRANCH}, found {branch}.")
    origin = normalized_origin(git(repo, "remote", "get-url", "origin"))
    if not origin.endswith(EXPECTED_REPOSITORY):
        raise RuntimeError(f"Unexpected origin: {origin}")
    ancestor = run(
        repo,
        "git",
        "merge-base",
        "--is-ancestor",
        EXPECTED_BASE,
        "HEAD",
        check=False,
    )
    if ancestor.returncode != 0:
        raise RuntimeError(
            f"Current HEAD must descend from backend baseline {EXPECTED_BASE}."
        )
    tracked = git(repo, "status", "--porcelain", "--untracked-files=no")
    if tracked:
        raise RuntimeError(
            "Tracked working tree must be clean. Commit Phase 0 before applying Phase 1."
        )

    for relative, expected_hash in PHASE0_HASHES.items():
        path = repo / relative
        if not path.is_file():
            raise RuntimeError(f"Phase 0 file is missing: {relative}")
        actual_hash = sha256_file(path)
        if actual_hash != expected_hash:
            raise RuntimeError(
                f"Phase 0 file changed unexpectedly: {relative}\n"
                f"expected {expected_hash}\nactual   {actual_hash}"
            )
    readme = (repo / "README.md").read_text(encoding="utf-8")
    apply_doc = (repo / "APPLY_AND_VALIDATE.md").read_text(encoding="utf-8")
    if PHASE0_MARKER not in readme or "ANGULAR_FRONTEND_PHASE_0_VALIDATION" not in apply_doc:
        raise RuntimeError("Phase 0 documentation markers are missing.")

    for relative in FILES:
        if (repo / relative).exists():
            raise RuntimeError(f"Phase 1 target already exists: {relative}")
    if (repo / "frontend/package-lock.json").exists():
        raise RuntimeError("Unexpected pre-existing frontend/package-lock.json.")
    if (repo / "frontend/node_modules").exists():
        raise RuntimeError("Unexpected pre-existing frontend/node_modules directory.")
    for relative, addition in APPENDS.items():
        path = repo / relative
        if not path.is_file():
            raise RuntimeError(f"Missing append target: {relative}")
        marker = next(
            line.strip("<!-> ")
            for line in addition.splitlines()
            if line.strip().startswith("<!--")
        )
        if marker in path.read_text(encoding="utf-8"):
            raise RuntimeError(f"Phase 1 marker already exists in {relative}")
    verify_node(repo)


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".phase1.tmp")
    temporary.write_text(content.rstrip() + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def remove_empty_parents(path: Path, stop: Path) -> None:
    current = path.parent
    while current != stop and current.is_dir():
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def validate_static(repo: Path) -> None:
    checks = (
        (sys.executable, "scripts/validate_frontend_contracts.py", "--repo", "."),
        (sys.executable, "scripts/validate_angular_phase1.py", "--repo", "."),
        (
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/test_frontend_contracts.py",
            "tests/test_angular_phase1_foundation.py",
        ),
        (sys.executable, "-m", "compileall", "-q", "scripts", "tests"),
        ("git", "diff", "--check"),
    )
    for command in checks:
        result = run(repo, *command, check=False)
        if result.returncode != 0:
            raise RuntimeError(
                "Post-apply static validation failed: "
                + " ".join(command)
                + "\n"
                + result.stdout
            )


def validate_npm(repo: Path) -> None:
    frontend = repo / "frontend"
    install = run(repo, NPM, "install", check=False, cwd=frontend)
    if install.returncode != 0:
        raise RuntimeError("npm install failed:\n" + install.stdout)
    validate = run(repo, NPM, "run", "validate:phase1", check=False, cwd=frontend)
    if validate.returncode != 0:
        raise RuntimeError("Angular Phase 1 validation failed:\n" + validate.stdout)


def apply(repo: Path, *, skip_install: bool) -> None:
    created: list[Path] = []
    backups: dict[Path, bytes] = {}
    generated_paths = [repo / "frontend/package-lock.json", repo / "frontend/node_modules"]
    try:
        for relative, content in FILES.items():
            path = repo / relative
            write_atomic(path, content)
            created.append(path)
        for relative, addition in APPENDS.items():
            path = repo / relative
            backups[path] = path.read_bytes()
            original = path.read_text(encoding="utf-8").rstrip()
            write_atomic(path, original + addition)
        validate_static(repo)
        if not skip_install:
            validate_npm(repo)
        print(
            "Applied Angular Phase 1 successfully: "
            f"{len(FILES)} new files, {len(APPENDS)} documentation updates, "
            "31 typed API operations."
        )
        if skip_install:
            print(
                "npm installation was skipped. Run `cd frontend && npm install && "
                "npm run validate:phase1` before committing."
            )
        else:
            print(
                "Run `cd frontend && npx playwright install chromium && npm run e2e` "
                "for the platform-specific browser smoke test."
            )
    except Exception:
        for path, content in backups.items():
            path.write_bytes(content)
        for generated in generated_paths:
            if generated.is_dir():
                shutil.rmtree(generated, ignore_errors=True)
            elif generated.exists():
                generated.unlink()
        for path in reversed(created):
            if path.exists():
                path.unlink()
            remove_empty_parents(path, repo)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply the complete Angular Phase 1 foundation."
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Write and statically validate files without npm install/build/tests.",
    )
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    verify_repo(repo)
    apply(repo, skip_install=args.skip_install)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exception:
        print(f"ERROR: {exception}", file=sys.stderr)
        raise SystemExit(1)
