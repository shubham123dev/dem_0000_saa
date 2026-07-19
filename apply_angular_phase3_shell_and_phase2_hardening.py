#!/usr/bin/env python3
"""Apply Phase 2 hardening and the complete Angular Phase 3 workplace shell."""
from __future__ import annotations
import argparse, hashlib, os, shutil, subprocess, sys
from pathlib import Path

EXPECTED_BRANCH='main'
EXPECTED_HEAD='047547b49fa296568d7bc3731ae605f69f2698b1'
EXPECTED_REPOSITORY='shubham123dev/dem_0000_saa'
EXPECTED_HASHES={'frontend/docs/DESIGN_SYSTEM.md': '80e5641ecceebcc08ca25a6695866d9614db39f5dcc2a36332d1eb41bd5d7f5a',
 'frontend/docs/PHASE_2_ACCEPTANCE.md': 'dda2dd84045a6f667fc228ac7f6747a85702e32a6d09d1ab2be14244799a9b19',
 'frontend/e2e/foundation.spec.ts': '7153b0bc07576b071e00056c3d2e4dbe4a172eafa5ca95363edec231a2351b9a',
 'frontend/package.json': 'f1da05bfe5663d58c8ae2e20d446766e41d15a1bd9d650960ed7d5fe446d19cf',
 'frontend/src/app/app.component.html': '458ae8a4c1c4744f96f26cd90f6ce3b90bcebf5c3a4a5ae0d45edf90b0529818',
 'frontend/src/app/app.component.scss': '741df5fbd98d40b007bd06df00800833d46c37e1b9fb9d08f9c1cf9b4fd659ae',
 'frontend/src/app/app.component.spec.ts': '97be72a55ad8638eba838c53d4a23ce66fbd4f467a44b0a3b40fb82ec1dee466',
 'frontend/src/app/app.component.ts': 'f087a4065d81585ea25e2d3e553f3411ea09a48d668e273d39e86e19d8b2457a',
 'frontend/src/app/shared/ui/index.ts': 'bca99ac850b678feccc3f0cf3199d7587aa1686c166b84dcf8cf6bf1cc814d4b',
 'frontend/src/app/shared/ui/ui-button/ui-button.component.scss': '8a0c9ead9531270e893fd1ec6e858bd7ba6e4cf02f251ff5c134f5432b5198da',
 'frontend/src/app/shared/ui/ui-input/ui-input.component.html': 'cc94e9f5a056c48f6c36f19236521a2f616dfaaa803a09150c4dcf9ba93f85b9',
 'frontend/src/app/shared/ui/ui-input/ui-input.component.spec.ts': '7e08d2e65e40d2d4cb5ea32c6bc619a456082d40cc20b03adf1e3f512992219d',
 'frontend/src/app/shared/ui/ui-input/ui-input.component.ts': '17074f3a57dc7a99f65563d90784933fb111afe10beaf3d5ae2b769b23f22a2b',
 'frontend/src/app/shared/ui/ui-surface/ui-surface.component.scss': '5ada35ce8feacff5d12e0e54476325da6027e7866ebbeba6ceb0a7ff1d860727',
 'frontend/src/app/shared/ui/ui-surface/ui-surface.component.ts': '022bfb6ef42363c7b9dc8e7c77ce37a9388045079fad81f8e9f5d101aff4a937',
 'frontend/src/app/shared/ui/ui-textarea/ui-textarea.component.html': '6dddb37918b9861da6186d0d82aec25c42f290cb50bfc844a91f218b789681b7',
 'frontend/src/app/shared/ui/ui-textarea/ui-textarea.component.ts': 'd7752f2c37f3ed5bc1c43c0e3c5e9b9ef54ff88adee081d55f39eee1521f1f76',
 'frontend/src/index.html': '6176c6da6adc33ca7f3894cdb2005716971b309a92bfdba55fb87523c6b78d48',
 'frontend/src/styles/_tokens.scss': '978cbb64152a2cf133dfa95bfa2ac96a3df7c4ab27858b7191e37eaad1b89da1',
 'scripts/validate_angular_phase2.py': 'aa97df568f4c86155127a94f1a17dd3ba4d85b9a9ef0cf0985fcd5e28d44b2c4',
 'tests/test_angular_phase2.py': '0f4d40dd829ceecd6cdaa20b21ab2921ba4bf6e219a6d0fbf6faccda8bc4b7de'}
REPLACEMENTS={'frontend/docs/DESIGN_SYSTEM.md': '# Angular workplace-agent design system\n'
                                   '\n'
                                   'Phase 2 established the visual contract, and the Phase 3 hardening pass closes the remaining accessibility and '
                                   'product-exposure gaps.\n'
                                   '\n'
                                   '## Principles\n'
                                   '\n'
                                   '- Semantic CSS custom properties are the only source of product color, spacing, radius, shadow, typography, and motion.\n'
                                   '- Light and dark themes change semantic values, not component rules.\n'
                                   '- Theme preference is applied before Angular bootstrap to prevent a light-theme flash.\n'
                                   '- Components use `ChangeDetectionStrategy.OnPush` and expose native accessibility semantics.\n'
                                   '- Status colors are never the only indicator; labels remain visible and light-theme text/background pairs meet the '
                                   'normal-text contrast target.\n'
                                   '- Input and textarea primitives implement `ControlValueAccessor` for reactive and template-driven forms.\n'
                                   '- Clickable cards use the native-button `UiActionSurface`; presentational `UiSurface` never pretends to be interactive.\n'
                                   '- The UI does not expose API routes, model prompts, SQL, internal actor IDs, organization IDs, or backend-owned policy '
                                   'calculations.\n'
                                   '\n'
                                   '## Included primitives\n'
                                   '\n'
                                   '`UiActionSurface`, `UiButton`, `UiIconButton`, `UiBadge`, `UiSurface`, `UiCallout`, `UiStatusIndicator`, `UiInput`, '
                                   '`UiTextarea`, `UiSpinner`, and `UiSkeleton`.\n'
                                   '\n'
                                   '## Theme contract\n'
                                   '\n'
                                   '`UiThemeService` supports `system`, `light`, and `dark`. Explicit choices persist in local storage. System mode follows '
                                   '`prefers-color-scheme`. The pre-bootstrap initializer and Angular service use the same storage key and document '
                                   'attributes.\n'
                                   '\n'
                                   '## Styling rule\n'
                                   '\n'
                                   'Component SCSS must use semantic variables such as `--ui-surface-base` or `--ui-status-danger-fg`. New hexadecimal values '
                                   'belong only in `_tokens.scss` or `_themes.scss`.\n',
 'frontend/docs/PHASE_2_ACCEPTANCE.md': '# Phase 2 acceptance after hardening\n'
                                        '\n'
                                        'Phase 2 is complete when semantic themes and eleven primitives pass strict TypeScript, Angular template checks, '
                                        'ESLint, Vitest, production build, and browser tests. The quality gate additionally verifies pre-bootstrap theme '
                                        'initialization, reactive-form integration, native interactive semantics, normal-text contrast, and the absence of '
                                        'visible internal IDs or third-party branding.\n',
 'frontend/e2e/foundation.spec.ts': "import { expect, test } from '@playwright/test';\n"
                                    '\n'
                                    "test('renders and navigates the complete workplace shell', async ({ page }) => {\n"
                                    "  await page.goto('/');\n"
                                    '  await expect(page.getByRole(\'heading\', { name: "Let\'s get to work." })).toBeVisible();\n'
                                    '  const viewport = page.viewportSize();\n'
                                    '  if (viewport && viewport.width < 768) {\n'
                                    "    await page.getByRole('button', { name: 'Open navigation' }).click();\n"
                                    '  }\n'
                                    "  await page.getByRole('button', { name: /Users/ }).first().click();\n"
                                    "  await expect(page.getByRole('heading', { name: 'Users' })).toBeVisible();\n"
                                    "  await expect(page.locator('body')).not.toContainText('Cloudflare');\n"
                                    "  await expect(page.locator('body')).not.toContainText('/agent/actions/propose');\n"
                                    '});\n'
                                    '\n'
                                     "test('opens and closes the responsive Ask AI panel', async ({ page }) => {\n"
                                     "  await page.goto('/');\n"
                                     "  const panel = page.getByRole('complementary', { name: 'Ask AI' });\n"
                                     "  const close = panel.getByRole('button', { name: 'Close Ask AI' });\n"
                                     '  if (await close.count() === 0) {\n'
                                     "    await page.getByRole('button', { name: /Ask AI/ }).first().click();\n"
                                     '  }\n'
                                     '  await expect(close).toBeVisible();\n'
                                     '  await close.click();\n'
                                     '  await expect(panel).toHaveCount(0);\n'
                                     "  await page.getByRole('button', { name: /Ask AI/ }).first().click();\n"
                                     '  await expect(panel).toBeVisible();\n'
                                     '});\n'
                                    '\n'
                                    "test('persists the dark theme choice', async ({ page }) => {\n"
                                    "  await page.goto('/');\n"
                                    "  await page.getByRole('button', { name: 'Open account preferences' }).click();\n"
                                    "  await page.getByRole('button', { name: 'Use dark theme' }).click();\n"
                                    "  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');\n"
                                    '  await page.reload();\n'
                                    "  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');\n"
                                    '});\n',
 'frontend/package.json': '{\n'
                          '  "name": "dbmr-workplace-agent-ui",\n'
                          '  "version": "0.1.0",\n'
                          '  "private": true,\n'
                          '  "description": "Angular presentation layer for the governed DBMR Workplace Agent sandbox",\n'
                          '  "engines": {\n'
                          '    "node": "^20.19.0 || ^22.12.0 || ^24.0.0",\n'
                          '    "npm": ">=10"\n'
                          '  },\n'
                          '  "scripts": {\n'
                          '    "start": "ng serve --host 127.0.0.1 --port 4200 --proxy-config proxy.conf.json",\n'
                          '    "build": "ng build",\n'
                          '    "build:development": "ng build --configuration development",\n'
                          '    "typecheck": "tsc -p tsconfig.app.json --noEmit && tsc -p tsconfig.spec.json --noEmit && tsc -p tsconfig.e2e.json --noEmit",\n'
                          '    "lint": "eslint \\"src/**/*.ts\\" \\"src/**/*.html\\" \\"e2e/**/*.ts\\"",\n'
                          '    "test": "ng test --watch=false",\n'
                          '    "test:coverage": "ng test --watch=false --coverage",\n'
                          '    "e2e": "playwright test",\n'
                          '    "e2e:list": "playwright test --list",\n'
                          '    "quality:boundaries": "node scripts/check-architecture-boundaries.mjs",\n'
                          '    "validate:phase1": "npm run quality:boundaries && npm run typecheck && npm run lint && npm run test && npm run build && npm run '
                          'e2e:list",\n'
                          '    "validate:phase2": "npm run quality:boundaries && npm run typecheck && npm run lint && npm run test && npm run build && npm run '
                          'e2e:list",\n'
                          '    "validate:full": "npm run validate:phase3 && npm run e2e",\n'
                          '    "validate:phase3": "npm run quality:boundaries && npm run typecheck && npm run lint && npm run test && npm run build && npm run '
                          'e2e:list"\n'
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
 'frontend/src/app/app.component.html': '<app-shell />\n',
 'frontend/src/app/app.component.scss': ':host { display: block; min-height: 100dvh; }\n',
 'frontend/src/app/app.component.spec.ts': "import { TestBed } from '@angular/core/testing';\n"
                                           "import { describe, expect, it } from 'vitest';\n"
                                           "import { AppComponent } from './app.component';\n"
                                           '\n'
                                           "describe('AppComponent', () => {\n"
                                           "  it('renders the complete workplace shell', async () => {\n"
                                           '    localStorage.clear();\n'
                                           '    await TestBed.configureTestingModule({ imports: [AppComponent] }).compileComponents();\n'
                                           '    const fixture = TestBed.createComponent(AppComponent);\n'
                                           '    fixture.detectChanges();\n'
                                           '    const element = fixture.nativeElement as HTMLElement;\n'
                                           '    expect(element.textContent).toContain("Let\'s get to work.");\n'
                                           '    expect(element.querySelector(\'[aria-label="Primary navigation"]\')).not.toBeNull();\n'
                                           '    expect(element.querySelector(\'[aria-label="Ask AI"]\')).not.toBeNull();\n'
                                           '  });\n'
                                           '});\n',
 'frontend/src/app/app.component.ts': "import { ChangeDetectionStrategy, Component } from '@angular/core';\n"
                                      "import { AppShellComponent } from './layout/app-shell/app-shell.component';\n"
                                      '\n'
                                      '@Component({\n'
                                      "  selector: 'app-root',\n"
                                      '  standalone: true,\n'
                                      '  imports: [AppShellComponent],\n'
                                      '  changeDetection: ChangeDetectionStrategy.OnPush,\n'
                                      "  template: '<app-shell />'\n"
                                      '})\n'
                                      'export class AppComponent {}\n',
 'frontend/src/app/shared/ui/index.ts': "export * from './ui-action-surface/ui-action-surface.component';\n"
                                        "export * from './ui-badge/ui-badge.component';\n"
                                        "export * from './ui-button/ui-button.component';\n"
                                        "export * from './ui-callout/ui-callout.component';\n"
                                        "export * from './ui-icon-button/ui-icon-button.component';\n"
                                        "export * from './ui-input/ui-input.component';\n"
                                        "export * from './ui-skeleton/ui-skeleton.component';\n"
                                        "export * from './ui-spinner/ui-spinner.component';\n"
                                        "export * from './ui-status-indicator/ui-status-indicator.component';\n"
                                        "export * from './ui-surface/ui-surface.component';\n"
                                        "export * from './ui-textarea/ui-textarea.component';\n",
 'frontend/src/app/shared/ui/ui-button/ui-button.component.scss': ':host {\n'
                                                                  '  display: inline-flex;\n'
                                                                  '}\n'
                                                                  '\n'
                                                                  ':host:has(.ui-button--full) {\n'
                                                                  '  display: flex;\n'
                                                                  '  width: 100%;\n'
                                                                  '}\n'
                                                                  '\n'
                                                                  '.ui-button {\n'
                                                                  '  display: inline-flex;\n'
                                                                  '  min-width: max-content;\n'
                                                                  '  align-items: center;\n'
                                                                  '  justify-content: center;\n'
                                                                  '  gap: var(--ui-space-2);\n'
                                                                  '  border: 1px solid transparent;\n'
                                                                  '  border-radius: var(--ui-radius-sm);\n'
                                                                  '  font-weight: var(--ui-weight-semibold);\n'
                                                                  '  line-height: 1;\n'
                                                                  '  cursor: pointer;\n'
                                                                  '  transition: background var(--ui-duration-fast) var(--ui-ease-standard), border-color '
                                                                  'var(--ui-duration-fast) var(--ui-ease-standard), color var(--ui-duration-fast) '
                                                                  'var(--ui-ease-standard), box-shadow var(--ui-duration-fast) var(--ui-ease-standard), '
                                                                  'transform var(--ui-duration-fast) var(--ui-ease-standard);\n'
                                                                  '}\n'
                                                                  '\n'
                                                                  '.ui-button:hover:not(:disabled) {\n'
                                                                  '  box-shadow: var(--ui-shadow-xs);\n'
                                                                  '}\n'
                                                                  '\n'
                                                                  '.ui-button:active:not(:disabled) {\n'
                                                                  '  transform: translateY(1px);\n'
                                                                  '}\n'
                                                                  '\n'
                                                                  '.ui-button:disabled {\n'
                                                                  '  cursor: not-allowed;\n'
                                                                  '  opacity: 0.55;\n'
                                                                  '}\n'
                                                                  '\n'
                                                                  '.ui-button--small { min-height: var(--ui-control-sm); padding: 0 var(--ui-space-3); '
                                                                  'font-size: var(--ui-text-sm); }\n'
                                                                  '.ui-button--medium { min-height: var(--ui-control-md); padding: 0 var(--ui-space-4); '
                                                                  'font-size: var(--ui-text-md); }\n'
                                                                  '.ui-button--large { min-height: var(--ui-control-lg); padding: 0 var(--ui-space-5); '
                                                                  'font-size: var(--ui-text-lg); }\n'
                                                                  '.ui-button--full { width: 100%; }\n'
                                                                  '\n'
                                                                  '.ui-button--primary { background: var(--ui-brand-500); color: var(--ui-neutral-950); }\n'
                                                                  '.ui-button--primary:hover:not(:disabled) { background: var(--ui-brand-600); color: '
                                                                  'var(--ui-neutral-950); }\n'
                                                                  '.ui-button--secondary { background: var(--ui-surface-inverse); color: '
                                                                  'var(--ui-text-inverse); }\n'
                                                                  '.ui-button--outline { border-color: var(--ui-border-default); background: '
                                                                  'var(--ui-surface-base); color: var(--ui-text-primary); }\n'
                                                                  '.ui-button--outline:hover:not(:disabled),\n'
                                                                  '.ui-button--ghost:hover:not(:disabled) { background: var(--ui-surface-hover); }\n'
                                                                  '.ui-button--ghost { background: transparent; color: var(--ui-text-primary); }\n'
                                                                  '.ui-button--danger { background: var(--ui-status-danger-fg); color: var(--ui-neutral-0); '
                                                                  '}\n',
 'frontend/src/app/shared/ui/ui-input/ui-input.component.html': '<div class="field" [class.field--invalid]="error">\n'
                                                                '  <label class="field__label" [for]="inputId">\n'
                                                                '    {{ label }}\n'
                                                                '    @if (required) { <span aria-hidden="true">*</span> }\n'
                                                                '  </label>\n'
                                                                '  <div class="field__control">\n'
                                                                '    <ng-content select="[uiInputPrefix]" />\n'
                                                                '    <input\n'
                                                                '      [id]="inputId"\n'
                                                                '      [type]="type"\n'
                                                                '      [value]="value"\n'
                                                                '      [placeholder]="placeholder"\n'
                                                                '      [disabled]="isDisabled"\n'
                                                                '      [required]="required"\n'
                                                                '      [autocomplete]="autocomplete"\n'
                                                                '      [attr.aria-invalid]="error ? true : null"\n'
                                                                '      [attr.aria-describedby]="error ? inputId + \'-error\' : description ? inputId + '
                                                                '\'-description\' : null"\n'
                                                                '      (input)="update($event)"\n'
                                                                '      (blur)="markTouched()"\n'
                                                                '    >\n'
                                                                '    <ng-content select="[uiInputSuffix]" />\n'
                                                                '  </div>\n'
                                                                '  @if (error) {\n'
                                                                '    <p class="field__message field__message--error" [id]="inputId + \'-error\'">{{ error '
                                                                '}}</p>\n'
                                                                '  } @else if (description) {\n'
                                                                '    <p class="field__message" [id]="inputId + \'-description\'">{{ description }}</p>\n'
                                                                '  }\n'
                                                                '</div>\n',
 'frontend/src/app/shared/ui/ui-input/ui-input.component.spec.ts': "import { Component } from '@angular/core';\n"
                                                                   "import { TestBed } from '@angular/core/testing';\n"
                                                                   "import { FormControl, ReactiveFormsModule } from '@angular/forms';\n"
                                                                   "import { describe, expect, it } from 'vitest';\n"
                                                                   "import { UiInputComponent } from './ui-input.component';\n"
                                                                   '\n'
                                                                   '@Component({\n'
                                                                   '  standalone: true,\n'
                                                                   '  imports: [ReactiveFormsModule, UiInputComponent],\n'
                                                                   '  template: \'<app-ui-input label="Rule name" [formControl]="control" />\'\n'
                                                                   '})\n'
                                                                   "class InputHostComponent { readonly control = new FormControl('Initial', { nonNullable: "
                                                                   'true }); }\n'
                                                                   '\n'
                                                                   "describe('UiInputComponent', () => {\n"
                                                                   "  it('associates the label and validation message with the native input', async () => {\n"
                                                                   '    await TestBed.configureTestingModule({ imports: [UiInputComponent] '
                                                                   '}).compileComponents();\n'
                                                                   '    const fixture = TestBed.createComponent(UiInputComponent);\n'
                                                                   "    fixture.componentInstance.label = 'Rule name';\n"
                                                                   "    fixture.componentInstance.error = 'Already exists';\n"
                                                                   '    fixture.detectChanges();\n'
                                                                    "    const input = (fixture.nativeElement as HTMLElement).querySelector('input') as HTMLInputElement;\n"
                                                                    "    const label = (fixture.nativeElement as HTMLElement).querySelector('label') as HTMLLabelElement;\n"
                                                                    '    expect(label.htmlFor).toBe(input.id);\n'
                                                                    "    expect(input.getAttribute('aria-invalid')).toBe('true');\n"
                                                                    "    expect(input.getAttribute('aria-describedby')).toBe(`${input.id}-error`);\n"
                                                                    '  });\n'
                                                                    '\n'
                                                                    "  it('integrates with reactive forms in both directions', async () => {\n"
                                                                    '    await TestBed.configureTestingModule({ imports: [InputHostComponent] '
                                                                    '}).compileComponents();\n'
                                                                    '    const fixture = TestBed.createComponent(InputHostComponent);\n'
                                                                    '    fixture.detectChanges();\n'
                                                                    "    const input = (fixture.nativeElement as HTMLElement).querySelector('input') as HTMLInputElement;\n"
                                                                   "    expect(input.value).toBe('Initial');\n"
                                                                   "    fixture.componentInstance.control.setValue('Updated');\n"
                                                                   '    fixture.detectChanges();\n'
                                                                   "    expect(input.value).toBe('Updated');\n"
                                                                   "    input.value = 'Typed';\n"
                                                                   "    input.dispatchEvent(new Event('input'));\n"
                                                                   "    expect(fixture.componentInstance.control.value).toBe('Typed');\n"
                                                                   '  });\n'
                                                                   '});\n',
 'frontend/src/app/shared/ui/ui-input/ui-input.component.ts': 'import { ChangeDetectionStrategy, ChangeDetectorRef, Component, EventEmitter, forwardRef, inject, '
                                                               "Input, Output } from '@angular/core';\n"
                                                               "import { type ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';\n"
                                                               '\n'
                                                               'let nextInputId = 0;\n'
                                                               '\n'
                                                               '@Component({\n'
                                                               "  selector: 'app-ui-input',\n"
                                                               '  standalone: true,\n'
                                                               '  providers: [{ provide: NG_VALUE_ACCESSOR, useExisting: forwardRef(() => UiInputComponent), '
                                                               'multi: true }],\n'
                                                               '  changeDetection: ChangeDetectionStrategy.OnPush,\n'
                                                               "  templateUrl: './ui-input.component.html',\n"
                                                               "  styleUrl: './ui-input.component.scss'\n"
                                                               '})\n'
                                                               'export class UiInputComponent implements ControlValueAccessor {\n'
                                                               "  private modelValue = '';\n"
                                                               '  private formDisabled = false;\n'
                                                               '  private onChange: (value: string) => void = () => undefined;\n'
                                                               '  private onTouched: () => void = () => undefined;\n'
                                                               '  private readonly changeDetector = inject(ChangeDetectorRef);\n'
                                                               '\n'
                                                               "  @Input({ required: true }) label = '';\n"
                                                               '  @Input() inputId = `ui-input-${++nextInputId}`;\n'
                                                               "  @Input() type: 'text' | 'email' | 'search' | 'url' | 'tel' = 'text';\n"
                                                               "  @Input() placeholder = '';\n"
                                                               "  @Input() description = '';\n"
                                                               "  @Input() error = '';\n"
                                                               '  @Input() disabled = false;\n'
                                                               '  @Input() required = false;\n'
                                                               "  @Input() autocomplete = 'off';\n"
                                                               '  @Output() readonly valueChange = new EventEmitter<string>();\n'
                                                               '\n'
                                                               '  @Input()\n'
                                                               '  set value(value: string | null | undefined) {\n'
                                                               "    this.modelValue = value ?? '';\n"
                                                               '  }\n'
                                                               '  get value(): string { return this.modelValue; }\n'
                                                               '  get isDisabled(): boolean { return this.disabled || this.formDisabled; }\n'
                                                               '\n'
                                                               '  update(event: Event): void {\n'
                                                               '    const value = (event.target as HTMLInputElement).value;\n'
                                                               '    this.modelValue = value;\n'
                                                               '    this.valueChange.emit(value);\n'
                                                               '    this.onChange(value);\n'
                                                               '  }\n'
                                                               '\n'
                                                               '  markTouched(): void { this.onTouched(); }\n'
                                                               "  writeValue(value: string | null): void { this.modelValue = value ?? ''; "
                                                               'this.changeDetector.markForCheck(); }\n'
                                                               '  registerOnChange(fn: (value: string) => void): void { this.onChange = fn; }\n'
                                                               '  registerOnTouched(fn: () => void): void { this.onTouched = fn; }\n'
                                                               '  setDisabledState(disabled: boolean): void { this.formDisabled = disabled; '
                                                               'this.changeDetector.markForCheck(); }\n'
                                                               '}\n',
 'frontend/src/app/shared/ui/ui-surface/ui-surface.component.scss': ':host { display: block; }\n'
                                                                    '.surface {\n'
                                                                    '  height: 100%;\n'
                                                                    '  border: 1px solid var(--ui-border-subtle);\n'
                                                                    '  border-radius: var(--ui-radius-lg);\n'
                                                                    '  background: var(--ui-surface-base);\n'
                                                                    '  color: var(--ui-text-primary);\n'
                                                                    '}\n'
                                                                    '.surface--padded { padding: var(--ui-space-5); }\n'
                                                                    '.surface--subtle { background: var(--ui-surface-subtle); }\n'
                                                                    '.surface--muted { background: var(--ui-surface-muted); }\n'
                                                                    '.surface--raised { box-shadow: var(--ui-shadow-sm); }\n',
 'frontend/src/app/shared/ui/ui-surface/ui-surface.component.ts': "import { ChangeDetectionStrategy, Component, Input } from '@angular/core';\n"
                                                                  '\n'
                                                                  "export type UiSurfaceVariant = 'base' | 'subtle' | 'muted' | 'raised';\n"
                                                                  '\n'
                                                                  '@Component({\n'
                                                                  "  selector: 'app-ui-surface',\n"
                                                                  '  standalone: true,\n'
                                                                  '  changeDetection: ChangeDetectionStrategy.OnPush,\n'
                                                                  '  template: \'<div class="surface surface--{{ variant }}" '
                                                                  '[class.surface--padded]="padded"><ng-content /></div>\',\n'
                                                                  "  styleUrl: './ui-surface.component.scss'\n"
                                                                  '})\n'
                                                                  'export class UiSurfaceComponent {\n'
                                                                  "  @Input() variant: UiSurfaceVariant = 'base';\n"
                                                                  '  @Input() padded = true;\n'
                                                                  '}\n',
 'frontend/src/app/shared/ui/ui-textarea/ui-textarea.component.html': '<div class="field" [class.field--invalid]="error">\n'
                                                                      '  <div class="field__heading">\n'
                                                                      '    <label class="field__label" [for]="textareaId">{{ label }} @if (required) { <span '
                                                                      'aria-hidden="true">*</span> }</label>\n'
                                                                      '    @if (maxLength !== null) { <span class="field__count">{{ value.length }} / {{ '
                                                                      'maxLength }}</span> }\n'
                                                                      '  </div>\n'
                                                                      '  <textarea\n'
                                                                      '    [id]="textareaId"\n'
                                                                      '    [value]="value"\n'
                                                                      '    [placeholder]="placeholder"\n'
                                                                      '    [disabled]="isDisabled"\n'
                                                                      '    [required]="required"\n'
                                                                      '    [rows]="rows"\n'
                                                                      '    [attr.maxlength]="maxLength"\n'
                                                                      '    [attr.aria-invalid]="error ? true : null"\n'
                                                                      '    [attr.aria-describedby]="error ? textareaId + \'-error\' : description ? textareaId '
                                                                      '+ \'-description\' : null"\n'
                                                                      '    (input)="update($event)"\n'
                                                                      '    (blur)="markTouched()"\n'
                                                                      '  ></textarea>\n'
                                                                      '  @if (error) {\n'
                                                                      '    <p class="field__message field__message--error" [id]="textareaId + \'-error\'">{{ '
                                                                      'error }}</p>\n'
                                                                      '  } @else if (description) {\n'
                                                                      '    <p class="field__message" [id]="textareaId + \'-description\'">{{ description '
                                                                      '}}</p>\n'
                                                                      '  }\n'
                                                                      '</div>\n',
 'frontend/src/app/shared/ui/ui-textarea/ui-textarea.component.ts': 'import { ChangeDetectionStrategy, ChangeDetectorRef, Component, EventEmitter, forwardRef, inject, '
                                                                     "Input, Output } from '@angular/core';\n"
                                                                     "import { type ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';\n"
                                                                     '\n'
                                                                     'let nextTextareaId = 0;\n'
                                                                     '\n'
                                                                     '@Component({\n'
                                                                     "  selector: 'app-ui-textarea',\n"
                                                                     '  standalone: true,\n'
                                                                     '  providers: [{ provide: NG_VALUE_ACCESSOR, useExisting: forwardRef(() => '
                                                                     'UiTextareaComponent), multi: true }],\n'
                                                                     '  changeDetection: ChangeDetectionStrategy.OnPush,\n'
                                                                     "  templateUrl: './ui-textarea.component.html',\n"
                                                                     "  styleUrl: './ui-textarea.component.scss'\n"
                                                                     '})\n'
                                                                     'export class UiTextareaComponent implements ControlValueAccessor {\n'
                                                                     "  private modelValue = '';\n"
                                                                     '  private formDisabled = false;\n'
                                                                     '  private onChange: (value: string) => void = () => undefined;\n'
                                                                     '  private onTouched: () => void = () => undefined;\n'
                                                                     '  private readonly changeDetector = inject(ChangeDetectorRef);\n'
                                                                     '\n'
                                                                     "  @Input({ required: true }) label = '';\n"
                                                                     '  @Input() textareaId = `ui-textarea-${++nextTextareaId}`;\n'
                                                                     "  @Input() placeholder = '';\n"
                                                                     "  @Input() description = '';\n"
                                                                     "  @Input() error = '';\n"
                                                                     '  @Input() disabled = false;\n'
                                                                     '  @Input() required = false;\n'
                                                                     '  @Input() rows = 4;\n'
                                                                     '  @Input() maxLength: number | null = null;\n'
                                                                     '  @Output() readonly valueChange = new EventEmitter<string>();\n'
                                                                     '\n'
                                                                     '  @Input()\n'
                                                                     "  set value(value: string | null | undefined) { this.modelValue = value ?? ''; }\n"
                                                                     '  get value(): string { return this.modelValue; }\n'
                                                                     '  get isDisabled(): boolean { return this.disabled || this.formDisabled; }\n'
                                                                     '\n'
                                                                     '  update(event: Event): void {\n'
                                                                     '    const value = (event.target as HTMLTextAreaElement).value;\n'
                                                                     '    this.modelValue = value;\n'
                                                                     '    this.valueChange.emit(value);\n'
                                                                     '    this.onChange(value);\n'
                                                                     '  }\n'
                                                                     '\n'
                                                                     '  markTouched(): void { this.onTouched(); }\n'
                                                                     "  writeValue(value: string | null): void { this.modelValue = value ?? ''; "
                                                                     'this.changeDetector.markForCheck(); }\n'
                                                                     '  registerOnChange(fn: (value: string) => void): void { this.onChange = fn; }\n'
                                                                     '  registerOnTouched(fn: () => void): void { this.onTouched = fn; }\n'
                                                                     '  setDisabledState(disabled: boolean): void { this.formDisabled = disabled; '
                                                                     'this.changeDetector.markForCheck(); }\n'
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
                            '    <script>\n'
                            '      (() => {\n'
                            "        const storageKey = 'dbmr-workplace-theme';\n"
                            '        const root = document.documentElement;\n'
                            "        let preference = 'system';\n"
                            '        try {\n'
                            '          const stored = localStorage.getItem(storageKey);\n'
                            "          if (stored === 'light' || stored === 'dark' || stored === 'system') {\n"
                            '            preference = stored;\n'
                            '          }\n'
                            '        } catch {\n'
                            "          preference = 'system';\n"
                            '        }\n'
                            "        const systemDark = globalThis.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false;\n"
                            "        const resolved = preference === 'system' ? (systemDark ? 'dark' : 'light') : preference;\n"
                            "        root.dataset['theme'] = resolved;\n"
                            "        root.dataset['themePreference'] = preference;\n"
                            '        root.style.colorScheme = resolved;\n'
                            '      })();\n'
                            '    </script>\n'
                            '  </head>\n'
                            '  <body>\n'
                            '    <app-root></app-root>\n'
                            '    <noscript>This application requires JavaScript.</noscript>\n'
                            '  </body>\n'
                            '</html>\n',
 'frontend/src/styles/_tokens.scss': ':root {\n'
                                     '  color-scheme: light;\n'
                                     '\n'
                                     '  --ui-font-sans: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;\n'
                                     '  --ui-font-mono: "SFMono-Regular", Consolas, "Liberation Mono", monospace;\n'
                                     '\n'
                                     '  --ui-text-xs: 0.6875rem;\n'
                                     '  --ui-text-sm: 0.75rem;\n'
                                     '  --ui-text-md: 0.875rem;\n'
                                     '  --ui-text-lg: 1rem;\n'
                                     '  --ui-text-xl: 1.25rem;\n'
                                     '  --ui-text-2xl: clamp(1.75rem, 3vw, 2.375rem);\n'
                                     '\n'
                                     '  --ui-leading-tight: 1.2;\n'
                                     '  --ui-leading-normal: 1.45;\n'
                                     '  --ui-leading-relaxed: 1.65;\n'
                                     '\n'
                                     '  --ui-weight-regular: 400;\n'
                                     '  --ui-weight-medium: 500;\n'
                                     '  --ui-weight-semibold: 600;\n'
                                     '  --ui-weight-bold: 700;\n'
                                     '\n'
                                     '  --ui-space-0: 0;\n'
                                     '  --ui-space-1: 0.25rem;\n'
                                     '  --ui-space-2: 0.5rem;\n'
                                     '  --ui-space-3: 0.75rem;\n'
                                     '  --ui-space-4: 1rem;\n'
                                     '  --ui-space-5: 1.25rem;\n'
                                     '  --ui-space-6: 1.5rem;\n'
                                     '  --ui-space-8: 2rem;\n'
                                     '  --ui-space-10: 2.5rem;\n'
                                     '  --ui-space-12: 3rem;\n'
                                     '  --ui-space-16: 4rem;\n'
                                     '\n'
                                     '  --ui-radius-xs: 0.25rem;\n'
                                     '  --ui-radius-sm: 0.375rem;\n'
                                     '  --ui-radius-md: 0.625rem;\n'
                                     '  --ui-radius-lg: 0.875rem;\n'
                                     '  --ui-radius-xl: 1.125rem;\n'
                                     '  --ui-radius-pill: 999px;\n'
                                     '\n'
                                     '  --ui-control-sm: 2rem;\n'
                                     '  --ui-control-md: 2.5rem;\n'
                                     '  --ui-control-lg: 3rem;\n'
                                     '\n'
                                     '  --ui-brand-500: #f48120;\n'
                                     '  --ui-brand-600: #dd6f10;\n'
                                     '  --ui-brand-soft: #fff3e8;\n'
                                     '\n'
                                     '  --ui-neutral-0: #ffffff;\n'
                                     '  --ui-neutral-25: #fcfcfd;\n'
                                     '  --ui-neutral-50: #f7f7f8;\n'
                                     '  --ui-neutral-100: #efeff1;\n'
                                     '  --ui-neutral-200: #dedfe3;\n'
                                     '  --ui-neutral-300: #c8cad0;\n'
                                     '  --ui-neutral-500: #73767d;\n'
                                     '  --ui-neutral-600: #5b5e65;\n'
                                     '  --ui-neutral-700: #3e4147;\n'
                                     '  --ui-neutral-800: #25272b;\n'
                                     '  --ui-neutral-900: #17181b;\n'
                                     '  --ui-neutral-950: #0f1012;\n'
                                     '\n'
                                     '  --ui-blue-50: #eef5ff;\n'
                                     '  --ui-blue-600: #2563d9;\n'
                                     '  --ui-green-50: #edf9f3;\n'
                                     '  --ui-green-600: #16845a;\n'
                                     '  --ui-green-700: #0f704a;\n'
                                     '  --ui-amber-50: #fff7e5;\n'
                                     '  --ui-amber-700: #9d6100;\n'
                                     '  --ui-red-50: #fff0f0;\n'
                                     '  --ui-red-600: #c63838;\n'
                                     '\n'
                                     '  --ui-surface-canvas: var(--ui-neutral-50);\n'
                                     '  --ui-surface-base: var(--ui-neutral-0);\n'
                                     '  --ui-surface-subtle: var(--ui-neutral-25);\n'
                                     '  --ui-surface-muted: var(--ui-neutral-100);\n'
                                     '  --ui-surface-hover: #f2f2f4;\n'
                                     '  --ui-surface-selected: var(--ui-brand-soft);\n'
                                     '  --ui-surface-inverse: var(--ui-neutral-900);\n'
                                     '  --ui-surface-overlay: rgb(15 16 18 / 45%);\n'
                                     '\n'
                                     '  --ui-text-primary: var(--ui-neutral-900);\n'
                                     '  --ui-text-secondary: var(--ui-neutral-600);\n'
                                     '  --ui-text-muted: var(--ui-neutral-500);\n'
                                     '  --ui-text-inverse: var(--ui-neutral-0);\n'
                                     '  --ui-text-link: var(--ui-blue-600);\n'
                                     '\n'
                                     '  --ui-border-subtle: var(--ui-neutral-200);\n'
                                     '  --ui-border-default: var(--ui-neutral-300);\n'
                                     '  --ui-border-strong: var(--ui-neutral-500);\n'
                                     '  --ui-border-focus: var(--ui-blue-600);\n'
                                     '\n'
                                     '  --ui-status-info-bg: var(--ui-blue-50);\n'
                                     '  --ui-status-info-fg: var(--ui-blue-600);\n'
                                     '  --ui-status-success-bg: var(--ui-green-50);\n'
                                     '  --ui-status-success-fg: var(--ui-green-700);\n'
                                     '  --ui-status-warning-bg: var(--ui-amber-50);\n'
                                     '  --ui-status-warning-fg: var(--ui-amber-700);\n'
                                     '  --ui-status-danger-bg: var(--ui-red-50);\n'
                                     '  --ui-status-danger-fg: var(--ui-red-600);\n'
                                     '\n'
                                     '  --ui-shadow-xs: 0 1px 2px rgb(15 16 18 / 6%);\n'
                                     '  --ui-shadow-sm: 0 3px 10px rgb(15 16 18 / 8%);\n'
                                     '  --ui-shadow-md: 0 12px 32px rgb(15 16 18 / 12%);\n'
                                     '  --ui-shadow-lg: 0 24px 64px rgb(15 16 18 / 16%);\n'
                                     '\n'
                                     '  --ui-duration-fast: 100ms;\n'
                                     '  --ui-duration-standard: 180ms;\n'
                                     '  --ui-duration-panel: 220ms;\n'
                                     '  --ui-ease-standard: cubic-bezier(0.2, 0, 0, 1);\n'
                                     '\n'
                                     '  --ui-z-base: 0;\n'
                                     '  --ui-z-sticky: 20;\n'
                                     '  --ui-z-overlay: 40;\n'
                                     '  --ui-z-dialog: 60;\n'
                                     '  --ui-z-toast: 80;\n'
                                     '\n'
                                     '  --ui-shell-header-height: 3.75rem;\n'
                                     '  --ui-shell-sidebar-width: 16.25rem;\n'
                                     '  --ui-shell-assistant-width: 28rem;\n'
                                     '  --ui-shell-assistant-min: 22rem;\n'
                                     '  --ui-shell-assistant-max: 38rem;\n'
                                     '}\n',
 'scripts/validate_angular_phase2.py': '#!/usr/bin/env python3\n'
                                       'from __future__ import annotations\n'
                                       'import argparse, math, re\n'
                                       'from pathlib import Path\n'
                                       '\n'
                                       'COMPONENTS = '
                                       "('ui-action-surface','ui-badge','ui-button','ui-callout','ui-icon-button','ui-input','ui-skeleton','ui-spinner','ui-status-indicator','ui-surface','ui-textarea')\n"
                                       "HEX = re.compile(r'#[0-9a-fA-F]{6}\\b')\n"
                                       '\n'
                                       'def _rgb(value: str) -> tuple[float,float,float]:\n'
                                       "    value=value.lstrip('#'); return tuple(int(value[i:i+2],16)/255 for i in (0,2,4))  # type: ignore[return-value]\n"
                                       'def _luminance(value: str) -> float:\n'
                                       '    channels=[c/12.92 if c<=0.03928 else ((c+0.055)/1.055)**2.4 for c in _rgb(value)]\n'
                                       '    return 0.2126*channels[0]+0.7152*channels[1]+0.0722*channels[2]\n'
                                       'def contrast(a: str,b: str) -> float:\n'
                                       '    high,low=sorted((_luminance(a),_luminance(b)),reverse=True); return (high+0.05)/(low+0.05)\n'
                                       'def _token(text: str,name: str) -> str | None:\n'
                                       "    match=re.search(rf'{re.escape(name)}:\\s*(#[0-9a-fA-F]{{6}})',text); return match.group(1) if match else None\n"
                                       '\n'
                                       'def validate(repo: Path) -> list[str]:\n'
                                       "    errors=[]; frontend=repo/'frontend'; styles=frontend/'src/styles'; "
                                       "tokens=(styles/'_tokens.scss').read_text(encoding='utf-8')\n"
                                       '    for component in COMPONENTS:\n'
                                       "        directory=frontend/'src/app/shared/ui'/component\n"
                                       "        sources=list(directory.glob('*.component.ts'))\n"
                                       "        if len(sources)!=1: errors.append(f'{component}: expected exactly one component TypeScript file'); continue\n"
                                       "        if 'ChangeDetectionStrategy.OnPush' not in sources[0].read_text(encoding='utf-8'): "
                                       "errors.append(f'{component}: OnPush is required')\n"
                                       "        for scss in directory.glob('*.scss'):\n"
                                       "            if HEX.search(scss.read_text(encoding='utf-8')): errors.append(f'{scss.relative_to(repo)}: component "
                                       "styles must use tokens')\n"
                                       "    index=(frontend/'src/index.html').read_text(encoding='utf-8')\n"
                                       '    for required in (\'dbmr-workplace-theme\',"dataset[\'theme\']",\'prefers-color-scheme: dark\'):\n'
                                       "        if required not in index: errors.append(f'index.html: missing pre-bootstrap theme behavior {required}')\n"
                                       '    for rel in '
                                       "('src/app/shared/ui/ui-input/ui-input.component.ts','src/app/shared/ui/ui-textarea/ui-textarea.component.ts'):\n"
                                       "        text=(frontend/rel).read_text(encoding='utf-8')\n"
                                       "        for required in ('ControlValueAccessor','NG_VALUE_ACCESSOR','writeValue','setDisabledState'):\n"
                                       "            if required not in text: errors.append(f'{rel}: missing {required}')\n"
                                       "    surface=(frontend/'src/app/shared/ui/ui-surface/ui-surface.component.ts').read_text(encoding='utf-8')\n"
                                       "    if 'interactive' in surface: errors.append('UiSurface must remain presentational')\n"
                                       '    '
                                       "action=(frontend/'src/app/shared/ui/ui-action-surface/ui-action-surface.component.html').read_text(encoding='utf-8')\n"
                                       "    if '<button' not in action: errors.append('UiActionSurface must use a native button')\n"
                                       "    visible='\\n'.join(path.read_text(encoding='utf-8') for path in (frontend/'src/app').rglob('*.html'))\n"
                                       "    for forbidden in ('Cloudflare','currentUser.userId()','organizationId','/agent/actions/'):\n"
                                       "        if forbidden in visible: errors.append(f'visible templates expose forbidden value: {forbidden}')\n"
                                       "    brand=_token(tokens,'--ui-brand-600'); dark=_token(tokens,'--ui-neutral-950'); "
                                       "green=_token(tokens,'--ui-green-700'); green_bg=_token(tokens,'--ui-green-50')\n"
                                       "    if not all((brand,dark,green,green_bg)): errors.append('contrast tokens are missing')\n"
                                       '    else:\n'
                                       "        if contrast(brand,dark)<4.5: errors.append('brand hover contrast is below 4.5:1')\n"
                                       "        if contrast(green,green_bg)<4.5: errors.append('success contrast is below 4.5:1')\n"
                                       '    return errors\n'
                                       '\n'
                                       'def main()->int:\n'
                                       '    '
                                       "parser=argparse.ArgumentParser();parser.add_argument('--repo',default='.');args=parser.parse_args();errors=validate(Path(args.repo).resolve())\n"
                                       '    if errors:\n'
                                       "        print('Angular Phase 2 hardening validation failed:');[print(f'- {e}') for e in errors];return 1\n"
                                       "    print('Angular Phase 2 hardening is valid: contrast, theme bootstrap, forms, semantics, and exposure checks "
                                       "pass.');return 0\n"
                                       "if __name__=='__main__': raise SystemExit(main())\n",
 'tests/test_angular_phase2.py': 'from pathlib import Path\n'
                                 'from scripts.validate_angular_phase2 import contrast, validate\n'
                                 'ROOT=Path(__file__).resolve().parents[1]\n'
                                 'def test_phase2_hardening_contract()->None: assert validate(ROOT)==[]\n'
                                 'def test_contrast_math_rejects_low_contrast()->None:\n'
                                 "    assert contrast('#dd6f10','#ffffff')<4.5\n"
                                 "    assert contrast('#dd6f10','#0f1012')>=4.5\n"}
NEW_FILES={'frontend/docs/PHASE_3_ACCEPTANCE.md': '# Phase 3 acceptance\n'
                                        '\n'
                                        '- Phase 2 hardening validator passes.\n'
                                        '- The shell contains a global header, searchable primary navigation, workspace, Ask AI panel, resize handle, and '
                                        'responsive overlays.\n'
                                        '- Desktop, narrow, and compact layouts are covered.\n'
                                        '- Navigation changes the visible workspace section.\n'
                                        '- Ask AI opens, closes, and persists its desktop width.\n'
                                        '- No internal actor or organization identifier is rendered.\n'
                                        '- No third-party dashboard brand is rendered.\n'
                                        '- No fake agent message or activity stage is rendered.\n'
                                        '- Strict TypeScript, ESLint, Vitest, production build, Playwright discovery, actual Playwright browser tests, and the '
                                        'complete backend suite pass.\n',
 'frontend/docs/PHASE_3_SHELL.md': '# Phase 3 workplace shell\n'
                                   '\n'
                                   'Phase 3 replaces the design-system showcase with the production-shaped workplace shell:\n'
                                   '\n'
                                   '- thin brand strip and compact global header;\n'
                                   '- searchable grouped primary navigation;\n'
                                   '- central workspace with functional section navigation;\n'
                                   '- collapsible, resizable desktop Ask AI panel;\n'
                                   '- overlay panel at medium widths and full-width panel on compact screens;\n'
                                   '- compact navigation drawer with backdrop;\n'
                                   '- persisted assistant width and open state;\n'
                                   '- keyboard shortcut `Ctrl/Cmd + Shift + A` for Ask AI and Escape for overlays;\n'
                                   '- no fake chat, activity, approval, execution, or backend data.\n'
                                   '\n'
                                   'All visible navigation controls perform a real shell action. Live resource projections and conversation behavior remain in '
                                   'their dedicated later phases.\n',
 'frontend/src/app/layout/app-shell/app-shell.component.html': '<a class="skip-link" href="#main-content">Skip to content</a>\n'
                                                               '<div\n'
                                                               '  class="app-shell"\n'
                                                               '  [class.app-shell--assistant-open]="state.assistantOpen()"\n'
                                                               '  [class.app-shell--assistant-overlay]="state.assistantOverlay()"\n'
                                                               '  [style.--shell-assistant-current.px]="state.assistantOpen() && !state.assistantOverlay() ? '
                                                               'state.assistantWidth() : 0"\n'
                                                               '>\n'
                                                               '  <div class="brand-strip" aria-hidden="true"></div>\n'
                                                               '  <app-global-header\n'
                                                               '    class="shell-header"\n'
                                                               '    [sectionTitle]="sectionTitle"\n'
                                                               '    [compact]="state.isCompact()"\n'
                                                               '    [assistantOpen]="state.assistantOpen()"\n'
                                                               '    (navigationPressed)="state.openSidebar()"\n'
                                                               '    (assistantPressed)="state.toggleAssistant()"\n'
                                                               '  />\n'
                                                               '\n'
                                                               '  @if (state.isCompact() && state.sidebarOpen()) {\n'
                                                               '    <button type="button" class="shell-backdrop shell-backdrop--sidebar" aria-label="Close '
                                                               'navigation" (click)="state.closeSidebar()"></button>\n'
                                                               '  }\n'
                                                               '  <app-primary-sidebar\n'
                                                               '    class="shell-sidebar"\n'
                                                               '    [activeSection]="state.activeSection()"\n'
                                                               '    [compact]="state.isCompact()"\n'
                                                               '    [open]="state.sidebarOpen()"\n'
                                                               '    (sectionSelected)="navigate($event)"\n'
                                                               '    (closePressed)="state.closeSidebar()"\n'
                                                               '  />\n'
                                                               '\n'
                                                               '  <main id="main-content" class="shell-workspace" tabindex="-1">\n'
                                                               '    <app-workspace-dashboard [section]="state.activeSection()" (navigate)="navigate($event)" '
                                                               '(askAi)="askAboutCurrentSection()" />\n'
                                                               '  </main>\n'
                                                               '\n'
                                                               '  @if (state.assistantOpen()) {\n'
                                                               '    @if (state.assistantOverlay()) {\n'
                                                               '      <button type="button" class="shell-backdrop shell-backdrop--assistant" aria-label="Close '
                                                               'Ask AI" (click)="state.closeAssistant()"></button>\n'
                                                               '    }\n'
                                                               '    <section class="shell-assistant" aria-label="Ask AI panel">\n'
                                                               '      @if (!state.assistantOverlay()) {\n'
                                                               '        <app-assistant-resize-handle [width]="state.assistantWidth()" '
                                                               '(widthChange)="state.setAssistantWidth($event)" />\n'
                                                               '      }\n'
                                                               '      <app-assistant-panel [overlay]="state.assistantOverlay()" '
                                                               '(closePressed)="state.closeAssistant()" (sectionSelected)="navigate($event)" />\n'
                                                               '    </section>\n'
                                                               '  }\n'
                                                               '</div>\n',
 'frontend/src/app/layout/app-shell/app-shell.component.scss': ':host { display: block; min-height: 100dvh; }\n'
                                                               '.app-shell {\n'
                                                               '  --shell-assistant-current: var(--ui-shell-assistant-width);\n'
                                                               '  display: grid;\n'
                                                               '  min-height: 100dvh;\n'
                                                               '  grid-template-columns: var(--ui-shell-sidebar-width) minmax(0, 1fr) '
                                                               'var(--shell-assistant-current);\n'
                                                               '  grid-template-rows: var(--ui-shell-header-height) minmax(0, 1fr);\n'
                                                               "  grid-template-areas: 'header header header' 'sidebar workspace assistant';\n"
                                                               '  overflow: hidden;\n'
                                                               '  background: var(--ui-surface-canvas);\n'
                                                               '  color: var(--ui-text-primary);\n'
                                                               '  transition: grid-template-columns var(--ui-duration-panel) var(--ui-ease-standard);\n'
                                                               '}\n'
                                                               '.brand-strip { position: fixed; z-index: calc(var(--ui-z-sticky) + 1); top: 0; right: 0; left: '
                                                               '0; height: 0.25rem; background: linear-gradient(90deg, var(--ui-status-danger-fg), '
                                                               'var(--ui-brand-600)); }\n'
                                                               '.shell-header { grid-area: header; min-width: 0; }\n'
                                                               '.shell-sidebar { grid-area: sidebar; min-height: 0; }\n'
                                                               '.shell-workspace { grid-area: workspace; min-width: 0; min-height: 0; overflow: auto; '
                                                               'background: var(--ui-surface-base); }\n'
                                                               '.shell-assistant { position: relative; z-index: var(--ui-z-base); grid-area: assistant; '
                                                               'min-width: 0; min-height: 0; border-left: 1px solid var(--ui-border-subtle); background: '
                                                               'var(--ui-surface-base); }\n'
                                                               '.shell-backdrop { position: fixed; z-index: calc(var(--ui-z-overlay) - 1); inset: '
                                                               'var(--ui-shell-header-height) 0 0; border: 0; background: var(--ui-surface-overlay); cursor: '
                                                               'default; }\n'
                                                               '.shell-backdrop--sidebar { display: none; }\n'
                                                               '.skip-link { position: fixed; z-index: var(--ui-z-toast); top: var(--ui-space-2); left: '
                                                               'var(--ui-space-3); transform: translateY(-160%); border-radius: var(--ui-radius-sm); '
                                                               'background: var(--ui-surface-inverse); color: var(--ui-text-inverse); padding: '
                                                               'var(--ui-space-2) var(--ui-space-3); }\n'
                                                               '.skip-link:focus { transform: translateY(0); }\n'
                                                               '@media (max-width: 73.99rem) {\n'
                                                               '  .app-shell { grid-template-columns: var(--ui-shell-sidebar-width) minmax(0, 1fr); '
                                                               "grid-template-areas: 'header header' 'sidebar workspace'; }\n"
                                                               '  .shell-assistant { position: fixed; z-index: var(--ui-z-overlay); top: '
                                                               'var(--ui-shell-header-height); right: 0; bottom: 0; width: '
                                                               'min(var(--ui-shell-assistant-width), 92vw); border-left: 1px solid var(--ui-border-subtle); '
                                                               'box-shadow: var(--ui-shadow-lg); }\n'
                                                               '}\n'
                                                               '@media (max-width: 47.99rem) {\n'
                                                               "  .app-shell { grid-template-columns: minmax(0,1fr); grid-template-areas: 'header' "
                                                               "'workspace'; }\n"
                                                               '  .shell-sidebar { position: static; grid-area: unset; }\n'
                                                               '  .shell-backdrop--sidebar { display: block; }\n'
                                                               '  .shell-assistant { left: 0; width: auto; }\n'
                                                               '}\n',
 'frontend/src/app/layout/app-shell/app-shell.component.ts': 'import { ChangeDetectionStrategy, Component, HostListener, ViewChild, inject } from '
                                                             "'@angular/core';\n"
                                                             "import { AssistantPanelComponent } from '../assistant-panel/assistant-panel.component';\n"
                                                             'import { AssistantResizeHandleComponent } from '
                                                             "'../assistant-resize-handle/assistant-resize-handle.component';\n"
                                                             "import { GlobalHeaderComponent } from '../global-header/global-header.component';\n"
                                                             "import { PrimarySidebarComponent } from '../primary-sidebar/primary-sidebar.component';\n"
                                                             "import { navigationItem, type ShellSectionId } from '../shell/shell-navigation.model';\n"
                                                             "import { ShellStateService } from '../shell/shell-state.service';\n"
                                                             "import { WorkspaceDashboardComponent } from '../workspace/workspace-dashboard.component';\n"
                                                             '\n'
                                                             '@Component({\n'
                                                             "  selector: 'app-shell',\n"
                                                             '  standalone: true,\n'
                                                             '  imports: [AssistantPanelComponent, AssistantResizeHandleComponent, GlobalHeaderComponent, '
                                                             'PrimarySidebarComponent, WorkspaceDashboardComponent],\n'
                                                             '  changeDetection: ChangeDetectionStrategy.OnPush,\n'
                                                             "  templateUrl: './app-shell.component.html',\n"
                                                             "  styleUrl: './app-shell.component.scss'\n"
                                                             '})\n'
                                                             'export class AppShellComponent {\n'
                                                             '  @ViewChild(PrimarySidebarComponent) private sidebar?: PrimarySidebarComponent;\n'
                                                             '  readonly state = inject(ShellStateService);\n'
                                                             '  get sectionTitle(): string { return navigationItem(this.state.activeSection()).label; }\n'
                                                             '\n'
                                                             '  navigate(section: ShellSectionId): void {\n'
                                                             '    this.state.selectSection(section);\n'
                                                             '    if (this.state.assistantOverlay()) this.state.closeAssistant();\n'
                                                             '  }\n'
                                                             '  askAboutCurrentSection(): void { this.state.openAssistant(); }\n'
                                                             '\n'
                                                             "  @HostListener('document:keydown', ['$event'])\n"
                                                             '  shortcuts(event: KeyboardEvent): void {\n'
                                                             "    if (event.key === 'Escape') { this.state.closeOverlays(); return; }\n"
                                                             "    if ((event.ctrlKey || event.metaKey) && !event.shiftKey && event.key.toLowerCase() === 'k') "
                                                             '{\n'
                                                             '      event.preventDefault();\n'
                                                             '      if (this.state.isCompact()) this.state.openSidebar();\n'
                                                             '      queueMicrotask(() => this.sidebar?.focusSearch());\n'
                                                             '      return;\n'
                                                             '    }\n'
                                                             "    if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === 'a') "
                                                             '{\n'
                                                             '      event.preventDefault();\n'
                                                             '      this.state.toggleAssistant();\n'
                                                             '    }\n'
                                                             '  }\n'
                                                             '}\n',
 'frontend/src/app/layout/assistant-panel/assistant-panel.component.html': '<aside class="assistant-panel" aria-label="Ask AI" [cdkTrapFocus]="overlay" '
                                                                           '[cdkTrapFocusAutoCapture]="overlay">\n'
                                                                           '  <header>\n'
                                                                           '    <button type="button" class="assistant-title" '
                                                                           '(click)="resetPreview()"><strong>Ask AI preview</strong><span '
                                                                           'aria-hidden="true">⌄</span></button>\n'
                                                                           '    <div>\n'
                                                                           '      <button type="button" class="assistant-icon-button" aria-label="Reset Ask AI '
                                                                           'preview" (click)="resetPreview()">＋</button>\n'
                                                                           '      <button type="button" class="assistant-icon-button" aria-label="Close Ask '
                                                                           'AI" (click)="closePressed.emit()">×</button>\n'
                                                                           '    </div>\n'
                                                                           '  </header>\n'
                                                                           '  <div class="assistant-body ui-dot-grid">\n'
                                                                           '    <div class="assistant-help"><span>Need more help?</span><button type="button" '
                                                                           '(click)="announcement.set(\'Support guidance is available from the global Support '
                                                                           'menu.\')">Support</button></div>\n'
                                                                           '    <div class="assistant-hero">\n'
                                                                           '      <div class="assistant-cloud" '
                                                                           'aria-hidden="true"><span></span><span></span><span></span></div>\n'
                                                                           '      <h2>{{ greeting }}</h2>\n'
                                                                           '      <p>What workplace area would you like to open?</p>\n'
                                                                           '    </div>\n'
                                                                           '    <div class="assistant-suggestions">\n'
                                                                           '      @for (suggestion of suggestions; track suggestion.section) {\n'
                                                                           '        <button type="button" (click)="choose(suggestion)">\n'
                                                                           '          <span aria-hidden="true">{{ suggestion.icon }}</span>\n'
                                                                           '          <span><strong>{{ suggestion.label }}</strong><small>{{ suggestion.detail '
                                                                           '}}</small></span>\n'
                                                                           '          <span aria-hidden="true">›</span>\n'
                                                                           '        </button>\n'
                                                                           '      }\n'
                                                                           '    </div>\n'
                                                                           '    <app-ui-callout tone="warning" title="No simulated activity">\n'
                                                                           '      Phase 3 provides the complete panel shell. Real messages and safe backend '
                                                                           'activity events are connected in Phase 4 and Phase 5.\n'
                                                                           '    </app-ui-callout>\n'
                                                                           '  </div>\n'
                                                                           '  <footer>\n'
                                                                           '    <div class="privacy-note"><span>Conversation tools remain disabled until their '
                                                                           'backend contract is connected.</span></div>\n'
                                                                           '    <app-ui-button variant="outline" [fullWidth]="true" '
                                                                           '(pressed)="sectionSelected.emit(\'approvals\')">Open pending '
                                                                           'approvals</app-ui-button>\n'
                                                                           '    <p class="sr-only" aria-live="polite">{{ announcement() }}</p>\n'
                                                                           '  </footer>\n'
                                                                           '</aside>\n',
 'frontend/src/app/layout/assistant-panel/assistant-panel.component.scss': ':host { display: block; height: 100%; min-height: 0; }\n'
                                                                           '.assistant-panel { display: grid; height: 100%; min-height: 0; grid-template-rows: '
                                                                           'auto minmax(0, 1fr) auto; background: var(--ui-surface-base); }\n'
                                                                           'header { display: flex; min-height: var(--ui-shell-header-height); align-items: '
                                                                           'center; justify-content: space-between; border-bottom: 1px solid '
                                                                           'var(--ui-border-subtle); padding: 0 var(--ui-space-3); }\n'
                                                                           'header > div { display: flex; gap: var(--ui-space-1); }\n'
                                                                           '.assistant-title, .assistant-icon-button { border: 0; background: transparent; '
                                                                           'color: var(--ui-text-primary); cursor: pointer; }\n'
                                                                           '.assistant-title { display: inline-flex; align-items: center; gap: '
                                                                           'var(--ui-space-2); }\n'
                                                                           '.assistant-icon-button { display: inline-grid; width: var(--ui-control-sm); '
                                                                           'height: var(--ui-control-sm); place-items: center; border-radius: '
                                                                           'var(--ui-radius-pill); font-size: var(--ui-text-lg); }\n'
                                                                           '.assistant-icon-button:hover { background: var(--ui-surface-hover); }\n'
                                                                           '.assistant-body { min-height: 0; overflow-y: auto; padding: var(--ui-space-4); }\n'
                                                                           '.assistant-help { display: flex; align-items: center; justify-content: '
                                                                           'space-between; border: 1px solid var(--ui-border-subtle); border-radius: '
                                                                           'var(--ui-radius-md); background: var(--ui-surface-base); padding: '
                                                                           'var(--ui-space-2) var(--ui-space-3); font-size: var(--ui-text-sm); }\n'
                                                                           '.assistant-help button { border: 1px solid var(--ui-border-subtle); border-radius: '
                                                                           'var(--ui-radius-sm); background: var(--ui-surface-base); color: '
                                                                           'var(--ui-text-primary); padding: var(--ui-space-2) var(--ui-space-3); cursor: '
                                                                           'pointer; }\n'
                                                                           '.assistant-hero { display: grid; justify-items: center; gap: var(--ui-space-2); '
                                                                           'padding: var(--ui-space-12) 0 var(--ui-space-8); text-align: center; }\n'
                                                                           '.assistant-hero h2 { margin: 0; font-size: var(--ui-text-xl); }\n'
                                                                           '.assistant-hero p { margin: 0; color: var(--ui-text-secondary); font-size: '
                                                                           'var(--ui-text-sm); }\n'
                                                                           '.assistant-cloud { position: relative; width: 8rem; height: 4.5rem; filter: '
                                                                           'drop-shadow(0 0.5rem 1rem color-mix(in srgb, var(--ui-brand-500) 22%, '
                                                                           'transparent)); }\n'
                                                                           '.assistant-cloud span { position: absolute; bottom: 0.4rem; border-radius: '
                                                                           'var(--ui-radius-pill); background: linear-gradient(135deg, var(--ui-brand-soft), '
                                                                           'var(--ui-brand-500)); }\n'
                                                                           '.assistant-cloud span:nth-child(1) { left: 0; width: 3.3rem; height: 2.6rem; }\n'
                                                                           '.assistant-cloud span:nth-child(2) { left: 2rem; width: 4.7rem; height: 4.4rem; }\n'
                                                                           '.assistant-cloud span:nth-child(3) { right: 0; width: 3rem; height: 2.9rem; }\n'
                                                                           '.assistant-suggestions { display: grid; gap: var(--ui-space-2); margin-bottom: '
                                                                           'var(--ui-space-4); }\n'
                                                                           '.assistant-suggestions button { display: grid; grid-template-columns: 2rem '
                                                                           'minmax(0,1fr) auto; align-items: center; gap: var(--ui-space-3); border: 1px solid '
                                                                           'var(--ui-border-subtle); border-radius: var(--ui-radius-md); background: '
                                                                           'var(--ui-surface-subtle); color: var(--ui-text-primary); padding: '
                                                                           'var(--ui-space-3); text-align: left; cursor: pointer; }\n'
                                                                           '.assistant-suggestions button:hover { border-color: var(--ui-border-default); '
                                                                           'background: var(--ui-surface-base); box-shadow: var(--ui-shadow-xs); }\n'
                                                                           '.assistant-suggestions button > span:nth-child(2) { display: grid; }\n'
                                                                           '.assistant-suggestions small { color: var(--ui-text-muted); font-size: '
                                                                           'var(--ui-text-xs); }\n'
                                                                           'footer { display: grid; gap: var(--ui-space-3); border-top: 1px solid '
                                                                           'var(--ui-border-subtle); background: var(--ui-surface-base); padding: '
                                                                           'var(--ui-space-3); }\n'
                                                                           '.privacy-note { border: 1px solid var(--ui-border-subtle); border-radius: '
                                                                           'var(--ui-radius-md); background: var(--ui-surface-subtle); color: '
                                                                           'var(--ui-text-secondary); padding: var(--ui-space-3); font-size: '
                                                                           'var(--ui-text-xs); line-height: var(--ui-leading-normal); }\n',
 'frontend/src/app/layout/assistant-panel/assistant-panel.component.ts': "import { A11yModule } from '@angular/cdk/a11y';\n"
                                                                         'import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output, signal } '
                                                                         "from '@angular/core';\n"
                                                                         'import { UiBadgeComponent, UiButtonComponent, UiCalloutComponent } from '
                                                                         "'../../shared/ui';\n"
                                                                         "import type { ShellSectionId } from '../shell/shell-navigation.model';\n"
                                                                         '\n'
                                                                         'interface AssistantSuggestion { readonly label: string; readonly detail: string; '
                                                                         'readonly section: ShellSectionId; readonly icon: string; }\n'
                                                                         '\n'
                                                                         '@Component({\n'
                                                                         "  selector: 'app-assistant-panel',\n"
                                                                         '  standalone: true,\n'
                                                                         '  imports: [A11yModule, UiBadgeComponent, UiButtonComponent, UiCalloutComponent],\n'
                                                                         '  changeDetection: ChangeDetectionStrategy.OnPush,\n'
                                                                         "  templateUrl: './assistant-panel.component.html',\n"
                                                                         "  styleUrl: './assistant-panel.component.scss'\n"
                                                                         '})\n'
                                                                         'export class AssistantPanelComponent {\n'
                                                                         '  @Input() overlay = false;\n'
                                                                         '  @Output() readonly closePressed = new EventEmitter<void>();\n'
                                                                         '  @Output() readonly sectionSelected = new EventEmitter<ShellSectionId>();\n'
                                                                         "  readonly announcement = signal('');\n"
                                                                         '  readonly suggestions: readonly AssistantSuggestion[] = [\n'
                                                                         "    { label: 'Review pending approvals', detail: 'Open proposals awaiting a "
                                                                         "decision', section: 'approvals', icon: '✓' },\n"
                                                                         "    { label: 'Explore users and roles', detail: 'Open organization memberships', "
                                                                         "section: 'users', icon: '○' },\n"
                                                                         "    { label: 'Inspect report access', detail: 'Open report entitlements', section: "
                                                                         "'reports', icon: '▤' }\n"
                                                                         '  ];\n'
                                                                         '  readonly greeting = this.createGreeting();\n'
                                                                         '\n'
                                                                         '  choose(suggestion: AssistantSuggestion): void {\n'
                                                                         '    this.sectionSelected.emit(suggestion.section);\n'
                                                                         '    this.announcement.set(`${suggestion.label} opened in the workspace.`);\n'
                                                                         '  }\n'
                                                                         "  resetPreview(): void { this.announcement.set('Preview reset. Conversation tools "
                                                                         "arrive in Phase 4.'); }\n"
                                                                         '  private createGreeting(): string {\n'
                                                                         '    const hour = new Date().getHours();\n'
                                                                         "    return hour < 12 ? 'Good morning.' : hour < 18 ? 'Good afternoon.' : 'Good "
                                                                         "evening.';\n"
                                                                         '  }\n'
                                                                         '}\n',
 'frontend/src/app/layout/assistant-resize-handle/assistant-resize-handle.component.scss': ':host { position: absolute; z-index: var(--ui-z-sticky); top: 0; '
                                                                                           'bottom: 0; left: -0.25rem; display: block; width: 0.5rem; cursor: '
                                                                                           'col-resize; touch-action: none; }\n'
                                                                                           ':host::after { position: absolute; top: 0; bottom: 0; left: '
                                                                                           '0.2rem; width: 1px; background: var(--ui-border-subtle); content: '
                                                                                           "''; transition: width var(--ui-duration-fast) "
                                                                                           'var(--ui-ease-standard), background var(--ui-duration-fast) '
                                                                                           'var(--ui-ease-standard); }\n'
                                                                                           ':host(:hover)::after, :host(:focus-visible)::after { width: 2px; '
                                                                                           'background: var(--ui-border-focus); }\n',
 'frontend/src/app/layout/assistant-resize-handle/assistant-resize-handle.component.ts': "import { DOCUMENT } from '@angular/common';\n"
                                                                                         'import { ChangeDetectionStrategy, Component, EventEmitter, '
                                                                                         "HostListener, inject, Input, Output } from '@angular/core';\n"
                                                                                         '\n'
                                                                                         '@Component({\n'
                                                                                         "  selector: 'app-assistant-resize-handle',\n"
                                                                                         '  standalone: true,\n'
                                                                                         '  changeDetection: ChangeDetectionStrategy.OnPush,\n'
                                                                                         "  template: '',\n"
                                                                                         "  styleUrl: './assistant-resize-handle.component.scss',\n"
                                                                                         '  host: {\n'
                                                                                         "    role: 'separator',\n"
                                                                                         "    tabindex: '0',\n"
                                                                                         "    'aria-label': 'Resize Ask AI panel',\n"
                                                                                         "    'aria-orientation': 'vertical',\n"
                                                                                         "    '[attr.aria-valuemin]': '352',\n"
                                                                                         "    '[attr.aria-valuemax]': '608',\n"
                                                                                         "    '[attr.aria-valuenow]': 'width'\n"
                                                                                         '  }\n'
                                                                                         '})\n'
                                                                                         'export class AssistantResizeHandleComponent {\n'
                                                                                         '  private readonly document = inject(DOCUMENT);\n'
                                                                                         '  private cleanup: (() => void) | null = null;\n'
                                                                                         '  @Input({ required: true }) width = 448;\n'
                                                                                         '  @Output() readonly widthChange = new EventEmitter<number>();\n'
                                                                                         '\n'
                                                                                         "  @HostListener('pointerdown', ['$event'])\n"
                                                                                         '  start(event: PointerEvent): void {\n'
                                                                                         '    event.preventDefault();\n'
                                                                                         '    this.stop();\n'
                                                                                         '    const startX = event.clientX;\n'
                                                                                         '    const startWidth = this.width;\n'
                                                                                         '    const view = this.document.defaultView;\n'
                                                                                         '    if (!view) return;\n'
                                                                                         '    const move = (moveEvent: PointerEvent): void => '
                                                                                         'this.widthChange.emit(startWidth + startX - moveEvent.clientX);\n'
                                                                                         '    const up = (): void => this.stop();\n'
                                                                                         "    view.addEventListener('pointermove', move);\n"
                                                                                         "    view.addEventListener('pointerup', up, { once: true });\n"
                                                                                         "    this.cleanup = () => { view.removeEventListener('pointermove', "
                                                                                         "move); view.removeEventListener('pointerup', up); this.cleanup = "
                                                                                         'null; };\n'
                                                                                         '  }\n'
                                                                                         '\n'
                                                                                         "  @HostListener('keydown', ['$event'])\n"
                                                                                         '  keyboard(event: KeyboardEvent): void {\n'
                                                                                         "    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') "
                                                                                         'return;\n'
                                                                                         '    event.preventDefault();\n'
                                                                                         "    this.widthChange.emit(this.width + (event.key === 'ArrowLeft' ? "
                                                                                         '16 : -16));\n'
                                                                                         '  }\n'
                                                                                         '  private stop(): void { this.cleanup?.(); }\n'
                                                                                         '}\n',
 'frontend/src/app/layout/global-header/global-header.component.html': '<header class="global-header">\n'
                                                                       '  <div class="global-header__account">\n'
                                                                       '    @if (compact) {\n'
                                                                       '      <button type="button" class="header-icon-button" aria-label="Open navigation" '
                                                                       '(click)="navigationPressed.emit()">☰</button>\n'
                                                                       '    }\n'
                                                                       '    <span class="brand-mark" '
                                                                       'aria-hidden="true"><span></span><span></span><span></span></span>\n'
                                                                       '    <div class="brand-copy"><strong>Workplace Agent</strong><span>Sandbox '
                                                                       'workspace</span></div>\n'
                                                                       '  </div>\n'
                                                                       '\n'
                                                                       '  <div class="global-header__center">\n'
                                                                       '    <span class="section-title">{{ sectionTitle }}</span>\n'
                                                                       '    <nav aria-label="Global actions">\n'
                                                                       '      <button type="button" class="header-action" [attr.aria-pressed]="assistantOpen" '
                                                                       '(click)="assistantPressed.emit()"><span aria-hidden="true">✦</span> Ask AI</button>\n'
                                                                       '      <div class="header-popover-anchor header-support">\n'
                                                                       '        <button type="button" class="header-action" '
                                                                       '[attr.aria-expanded]="supportOpen()" (click)="toggleSupport()"><span '
                                                                       'aria-hidden="true">?</span> Support</button>\n'
                                                                       '        @if (supportOpen()) {\n'
                                                                       '          <div class="header-popover" role="dialog" aria-label="Support information">\n'
                                                                       '            <strong>Need help?</strong>\n'
                                                                       '            <p>Use Ask AI for workplace questions. Approval and execution controls '
                                                                       'remain backend governed.</p>\n'
                                                                       '          </div>\n'
                                                                       '        }\n'
                                                                       '      </div>\n'
                                                                       '      <div class="header-popover-anchor">\n'
                                                                       '        <button type="button" class="account-button" aria-label="Open account '
                                                                       'preferences" [attr.aria-expanded]="accountOpen()" '
                                                                       '(click)="toggleAccount()">S</button>\n'
                                                                       '        @if (accountOpen()) {\n'
                                                                       '          <div class="header-popover header-popover--account" role="dialog" '
                                                                       'aria-label="Account preferences">\n'
                                                                       '            <strong>Sandbox administrator</strong>\n'
                                                                       '            <span>Theme preference</span>\n'
                                                                       '            <app-ui-theme-toggle />\n'
                                                                       '          </div>\n'
                                                                       '        }\n'
                                                                       '      </div>\n'
                                                                       '    </nav>\n'
                                                                       '  </div>\n'
                                                                       '\n'
                                                                       '  <div class="global-header__assistant" '
                                                                       '[class.global-header__assistant--hidden]="!assistantOpen">\n'
                                                                       '    <strong>Ask AI preview</strong>\n'
                                                                       '    <span>Phase 3</span>\n'
                                                                       '  </div>\n'
                                                                       '</header>\n',
 'frontend/src/app/layout/global-header/global-header.component.scss': ':host { display: block; min-width: 0; }\n'
                                                                       '.global-header {\n'
                                                                       '  display: grid;\n'
                                                                       '  min-height: var(--ui-shell-header-height);\n'
                                                                       '  grid-template-columns: var(--ui-shell-sidebar-width) minmax(0, 1fr) '
                                                                       'var(--shell-assistant-current, var(--ui-shell-assistant-width));\n'
                                                                       '  border-bottom: 1px solid var(--ui-border-subtle);\n'
                                                                       '  background: var(--ui-surface-base);\n'
                                                                       '}\n'
                                                                       '.global-header__account, .global-header__center, .global-header__assistant { display: '
                                                                       'flex; min-width: 0; align-items: center; }\n'
                                                                       '.global-header__account { gap: var(--ui-space-3); border-right: 1px solid '
                                                                       'var(--ui-border-subtle); padding: 0 var(--ui-space-4); }\n'
                                                                       '.global-header__center { justify-content: space-between; gap: var(--ui-space-4); '
                                                                       'padding: 0 var(--ui-space-5); }\n'
                                                                       '.global-header__center nav { display: flex; align-items: center; gap: '
                                                                       'var(--ui-space-2); }\n'
                                                                       '.global-header__assistant { justify-content: space-between; gap: var(--ui-space-3); '
                                                                       'border-left: 1px solid var(--ui-border-subtle); padding: 0 var(--ui-space-4); '
                                                                       'overflow: hidden; }\n'
                                                                       '.global-header__assistant--hidden { visibility: hidden; }\n'
                                                                       '.global-header__assistant span, .brand-copy span { color: var(--ui-text-muted); '
                                                                       'font-size: var(--ui-text-xs); }\n'
                                                                       '.brand-copy { display: grid; min-width: 0; line-height: var(--ui-leading-tight); }\n'
                                                                       '.brand-copy strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '
                                                                       'font-size: var(--ui-text-md); }\n'
                                                                       '.brand-mark { position: relative; display: inline-block; width: 1.9rem; height: '
                                                                       '1.35rem; flex: 0 0 auto; }\n'
                                                                       '.brand-mark span { position: absolute; bottom: 0; border-radius: '
                                                                       'var(--ui-radius-pill); background: var(--ui-brand-500); }\n'
                                                                       '.brand-mark span:nth-child(1) { left: 0; width: 1rem; height: 0.75rem; }\n'
                                                                       '.brand-mark span:nth-child(2) { left: 0.55rem; width: 1.15rem; height: 1.15rem; }\n'
                                                                       '.brand-mark span:nth-child(3) { right: 0; width: 0.85rem; height: 0.72rem; }\n'
                                                                       '.section-title { overflow: hidden; color: var(--ui-text-secondary); font-size: '
                                                                       'var(--ui-text-sm); text-overflow: ellipsis; white-space: nowrap; }\n'
                                                                       '.header-action, .header-icon-button, .account-button { border: 0; background: '
                                                                       'transparent; color: var(--ui-text-primary); cursor: pointer; }\n'
                                                                       '.header-action { display: inline-flex; min-height: var(--ui-control-sm); align-items: '
                                                                       'center; gap: var(--ui-space-2); border-radius: var(--ui-radius-sm); padding: 0 '
                                                                       'var(--ui-space-3); font-size: var(--ui-text-md); }\n'
                                                                       '.header-action:hover, .header-icon-button:hover, .account-button:hover { background: '
                                                                       'var(--ui-surface-hover); }\n'
                                                                       '.header-icon-button, .account-button { display: inline-grid; width: '
                                                                       'var(--ui-control-sm); height: var(--ui-control-sm); place-items: center; '
                                                                       'border-radius: var(--ui-radius-pill); }\n'
                                                                       '.account-button { background: var(--ui-surface-inverse); color: '
                                                                       'var(--ui-text-inverse); font-weight: var(--ui-weight-semibold); }\n'
                                                                       '.header-popover-anchor { position: relative; }\n'
                                                                       '.header-popover { position: absolute; z-index: var(--ui-z-overlay); top: calc(100% + '
                                                                       'var(--ui-space-2)); right: 0; display: grid; width: 18rem; gap: var(--ui-space-2); '
                                                                       'border: 1px solid var(--ui-border-subtle); border-radius: var(--ui-radius-md); '
                                                                       'background: var(--ui-surface-base); box-shadow: var(--ui-shadow-md); padding: '
                                                                       'var(--ui-space-4); }\n'
                                                                       '.header-popover p { margin: 0; color: var(--ui-text-secondary); font-size: '
                                                                       'var(--ui-text-sm); line-height: var(--ui-leading-normal); }\n'
                                                                       '.header-popover--account { gap: var(--ui-space-3); }\n'
                                                                       '.header-popover--account > span { color: var(--ui-text-muted); font-size: '
                                                                       'var(--ui-text-xs); }\n'
                                                                       '@media (max-width: 73.99rem) {\n'
                                                                       '  .global-header { grid-template-columns: var(--ui-shell-sidebar-width) minmax(0, '
                                                                       '1fr); }\n'
                                                                       '  .global-header__assistant { display: none; }\n'
                                                                       '}\n'
                                                                       '@media (max-width: 47.99rem) {\n'
                                                                       '  .global-header { grid-template-columns: 1fr; }\n'
                                                                       '  .global-header__account { border-right: 0; }\n'
                                                                       '  .global-header__center { position: absolute; right: var(--ui-space-3); height: '
                                                                       'var(--ui-shell-header-height); padding: 0; }\n'
                                                                       '  .global-header__center .section-title, .global-header__center .header-support { '
                                                                       'display: none; }\n'
                                                                       '  .brand-copy span { display: none; }\n'
                                                                       '}\n',
 'frontend/src/app/layout/global-header/global-header.component.ts': 'import { ChangeDetectionStrategy, Component, EventEmitter, HostListener, Input, Output, '
                                                                     "signal } from '@angular/core';\n"
                                                                     "import { UiThemeToggleComponent } from '../../shared/theme/ui-theme-toggle.component';\n"
                                                                     '\n'
                                                                     '@Component({\n'
                                                                     "  selector: 'app-global-header',\n"
                                                                     '  standalone: true,\n'
                                                                     '  imports: [UiThemeToggleComponent],\n'
                                                                     '  changeDetection: ChangeDetectionStrategy.OnPush,\n'
                                                                     "  templateUrl: './global-header.component.html',\n"
                                                                     "  styleUrl: './global-header.component.scss'\n"
                                                                     '})\n'
                                                                     'export class GlobalHeaderComponent {\n'
                                                                     "  @Input({ required: true }) sectionTitle = '';\n"
                                                                     '  @Input() compact = false;\n'
                                                                     '  @Input() assistantOpen = true;\n'
                                                                     '  @Output() readonly navigationPressed = new EventEmitter<void>();\n'
                                                                     '  @Output() readonly assistantPressed = new EventEmitter<void>();\n'
                                                                     '  readonly supportOpen = signal(false);\n'
                                                                     '  readonly accountOpen = signal(false);\n'
                                                                     '\n'
                                                                     '  toggleSupport(): void { this.supportOpen.update((open) => !open); '
                                                                     'this.accountOpen.set(false); }\n'
                                                                     '  toggleAccount(): void { this.accountOpen.update((open) => !open); '
                                                                     'this.supportOpen.set(false); }\n'
                                                                     "  @HostListener('document:keydown.escape')\n"
                                                                     '  closeMenus(): void { this.supportOpen.set(false); this.accountOpen.set(false); }\n'
                                                                     '}\n',
 'frontend/src/app/layout/primary-sidebar/primary-sidebar.component.html': '<aside class="sidebar" [class.sidebar--open]="open" aria-label="Primary '
                                                                           'navigation">\n'
                                                                           '  <div class="sidebar__top">\n'
                                                                           '    @if (compact) {\n'
                                                                           '      <button type="button" class="sidebar__close" aria-label="Close navigation" '
                                                                           '(click)="closePressed.emit()">×</button>\n'
                                                                           '    }\n'
                                                                           '    <label class="sidebar-search">\n'
                                                                           '      <span aria-hidden="true">⌕</span>\n'
                                                                           '      <span class="sr-only">Search navigation</span>\n'
                                                                           '      <input #searchInput type="search" placeholder="Quick search…" '
                                                                           '[value]="query" (input)="updateQuery($event)">\n'
                                                                           '      <kbd>Ctrl K</kbd>\n'
                                                                           '    </label>\n'
                                                                           '  </div>\n'
                                                                           '  <nav aria-label="Primary">\n'
                                                                           '    @for (group of groups; track group) {\n'
                                                                           '      <section>\n'
                                                                           '        <h2>{{ group }}</h2>\n'
                                                                           '        @for (item of items(group); track item.id) {\n'
                                                                           '          <button type="button" class="nav-item" '
                                                                           '[class.nav-item--active]="activeSection === item.id" '
                                                                           '[attr.aria-current]="activeSection === item.id ? \'page\' : null" '
                                                                           '(click)="sectionSelected.emit(item.id)">\n'
                                                                           '            <span class="nav-item__icon" aria-hidden="true">{{ item.icon '
                                                                           '}}</span>\n'
                                                                           '            <span>{{ item.label }}</span>\n'
                                                                           '            <span class="nav-item__arrow" aria-hidden="true">›</span>\n'
                                                                           '          </button>\n'
                                                                           '        } @empty {\n'
                                                                           '          <p class="sidebar__empty">No matching sections.</p>\n'
                                                                           '        }\n'
                                                                           '      </section>\n'
                                                                           '    }\n'
                                                                           '  </nav>\n'
                                                                           '  <footer>\n'
                                                                           '    <span class="status-dot" aria-hidden="true"></span>\n'
                                                                           '    <span><strong>Sandbox ready</strong><small>Governed actions '
                                                                           'enabled</small></span>\n'
                                                                           '  </footer>\n'
                                                                           '</aside>\n',
 'frontend/src/app/layout/primary-sidebar/primary-sidebar.component.scss': ':host { display: block; min-height: 0; }\n'
                                                                           '.sidebar { display: flex; height: 100%; min-height: 0; flex-direction: column; '
                                                                           'border-right: 1px solid var(--ui-border-subtle); background: '
                                                                           'var(--ui-surface-subtle); }\n'
                                                                           '.sidebar__top { position: relative; padding: var(--ui-space-4) var(--ui-space-3) '
                                                                           'var(--ui-space-2); }\n'
                                                                           '.sidebar__close { position: absolute; top: var(--ui-space-2); right: '
                                                                           'var(--ui-space-2); display: none; width: var(--ui-control-sm); height: '
                                                                           'var(--ui-control-sm); border: 0; border-radius: var(--ui-radius-pill); background: '
                                                                           'transparent; color: var(--ui-text-primary); font-size: var(--ui-text-xl); cursor: '
                                                                           'pointer; }\n'
                                                                           '.sidebar-search { display: flex; min-height: 2.25rem; align-items: center; gap: '
                                                                           'var(--ui-space-2); border: 1px solid var(--ui-border-subtle); border-radius: '
                                                                           'var(--ui-radius-md); background: var(--ui-surface-base); padding: 0 '
                                                                           'var(--ui-space-3); box-shadow: var(--ui-shadow-xs); }\n'
                                                                           '.sidebar-search input { min-width: 0; flex: 1; border: 0; outline: 0; background: '
                                                                           'transparent; color: var(--ui-text-primary); }\n'
                                                                           '.sidebar-search input::placeholder { color: var(--ui-text-muted); }\n'
                                                                           'kbd { border: 1px solid var(--ui-border-subtle); border-radius: '
                                                                           'var(--ui-radius-xs); background: var(--ui-surface-muted); color: '
                                                                           'var(--ui-text-muted); padding: 0.1rem 0.3rem; font: inherit; font-size: '
                                                                           'var(--ui-text-xs); }\n'
                                                                           'nav { flex: 1; overflow-y: auto; padding: 0 var(--ui-space-3) var(--ui-space-4); '
                                                                           '}\n'
                                                                           'nav section + section { margin-top: var(--ui-space-5); }\n'
                                                                           'nav h2 { margin: var(--ui-space-4) var(--ui-space-3) var(--ui-space-2); color: '
                                                                           'var(--ui-text-muted); font-size: var(--ui-text-xs); font-weight: '
                                                                           'var(--ui-weight-semibold); letter-spacing: 0.04em; text-transform: uppercase; }\n'
                                                                           '.nav-item { display: grid; width: 100%; min-height: 2.25rem; '
                                                                           'grid-template-columns: 1.5rem minmax(0,1fr) auto; align-items: center; gap: '
                                                                           'var(--ui-space-2); border: 0; border-radius: var(--ui-radius-sm); background: '
                                                                           'transparent; color: var(--ui-text-primary); padding: 0 var(--ui-space-3); '
                                                                           'text-align: left; cursor: pointer; }\n'
                                                                           '.nav-item:hover { background: var(--ui-surface-hover); }\n'
                                                                           '.nav-item--active { background: var(--ui-surface-muted); font-weight: '
                                                                           'var(--ui-weight-medium); }\n'
                                                                           '.nav-item__icon { color: var(--ui-text-muted); text-align: center; }\n'
                                                                           '.nav-item__arrow { color: var(--ui-text-muted); }\n'
                                                                           '.sidebar__empty { margin: var(--ui-space-3); color: var(--ui-text-muted); '
                                                                           'font-size: var(--ui-text-sm); }\n'
                                                                           'footer { display: flex; align-items: center; gap: var(--ui-space-3); border-top: '
                                                                           '1px solid var(--ui-border-subtle); padding: var(--ui-space-4); }\n'
                                                                           'footer > span:last-child { display: grid; }\n'
                                                                           'footer strong { font-size: var(--ui-text-sm); }\n'
                                                                           'footer small { color: var(--ui-text-muted); font-size: var(--ui-text-xs); }\n'
                                                                           '.status-dot { width: 0.625rem; height: 0.625rem; border-radius: '
                                                                           'var(--ui-radius-pill); background: var(--ui-status-success-fg); box-shadow: 0 0 0 '
                                                                           '3px var(--ui-status-success-bg); }\n'
                                                                           '@media (max-width: 47.99rem) {\n'
                                                                           '  .sidebar { position: fixed; z-index: var(--ui-z-dialog); top: '
                                                                           'var(--ui-shell-header-height); bottom: 0; left: 0; width: min(20rem, 88vw); '
                                                                           'transform: translateX(-102%); box-shadow: var(--ui-shadow-lg); transition: '
                                                                           'transform var(--ui-duration-panel) var(--ui-ease-standard); }\n'
                                                                           '  .sidebar--open { transform: translateX(0); }\n'
                                                                           '  .sidebar__close { display: inline-grid; place-items: center; }\n'
                                                                           '  .sidebar__top { padding-top: var(--ui-space-6); }\n'
                                                                           '}\n',
 'frontend/src/app/layout/primary-sidebar/primary-sidebar.component.ts': 'import { ChangeDetectionStrategy, Component, type ElementRef, EventEmitter, Input, '
                                                                          "Output, ViewChild } from '@angular/core';\n"
                                                                         'import { SHELL_NAVIGATION, type ShellNavigationItem, type ShellSectionId } from '
                                                                         "'../shell/shell-navigation.model';\n"
                                                                         '\n'
                                                                         '@Component({\n'
                                                                         "  selector: 'app-primary-sidebar',\n"
                                                                         '  standalone: true,\n'
                                                                         '  changeDetection: ChangeDetectionStrategy.OnPush,\n'
                                                                         "  templateUrl: './primary-sidebar.component.html',\n"
                                                                         "  styleUrl: './primary-sidebar.component.scss'\n"
                                                                         '})\n'
                                                                         'export class PrimarySidebarComponent {\n'
                                                                         "  @Input({ required: true }) activeSection: ShellSectionId = 'home';\n"
                                                                         '  @Input() compact = false;\n'
                                                                         '  @Input() open = false;\n'
                                                                         '  @Output() readonly sectionSelected = new EventEmitter<ShellSectionId>();\n'
                                                                         '  @Output() readonly closePressed = new EventEmitter<void>();\n'
                                                                         "  @ViewChild('searchInput') private searchInput?: ElementRef<HTMLInputElement>;\n"
                                                                         "  query = '';\n"
                                                                         '\n'
                                                                         "  get groups(): readonly ('Workspace' | 'Governance')[] { return ['Workspace', "
                                                                         "'Governance']; }\n"
                                                                         "  items(group: 'Workspace' | 'Governance'): readonly ShellNavigationItem[] {\n"
                                                                         '    const term = this.query.trim().toLowerCase();\n'
                                                                         '    return SHELL_NAVIGATION.filter((item) => item.group === group && (!term || '
                                                                         '[item.label,item.description,...item.keywords].some((value) => '
                                                                         'value.toLowerCase().includes(term))));\n'
                                                                         '  }\n'
                                                                         '  updateQuery(event: Event): void { this.query = (event.target as '
                                                                         'HTMLInputElement).value; }\n'
                                                                         '  focusSearch(): void { this.searchInput?.nativeElement.focus(); }\n'
                                                                         '}\n',
 'frontend/src/app/layout/shell/shell-navigation.model.ts': 'export type ShellSectionId =\n'
                                                            "  | 'home'\n"
                                                            "  | 'organizations'\n"
                                                            "  | 'users'\n"
                                                            "  | 'seats'\n"
                                                            "  | 'reports'\n"
                                                            "  | 'access-packages'\n"
                                                            "  | 'settings'\n"
                                                            "  | 'approvals'\n"
                                                            "  | 'audit';\n"
                                                            '\n'
                                                            'export interface ShellNavigationItem {\n'
                                                            '  id: ShellSectionId;\n'
                                                            '  label: string;\n'
                                                            '  description: string;\n'
                                                            '  icon: string;\n'
                                                            "  group: 'Workspace' | 'Governance';\n"
                                                            '  keywords: readonly string[];\n'
                                                            '}\n'
                                                            '\n'
                                                            'export const SHELL_NAVIGATION: readonly ShellNavigationItem[] = [\n'
                                                            "  { id: 'home', label: 'Workspace home', description: 'Overview and common tasks', icon: '⌂', "
                                                            "group: 'Workspace', keywords: ['home','overview'] },\n"
                                                            "  { id: 'organizations', label: 'Organizations', description: 'Profiles and workspace status', "
                                                            "icon: '◇', group: 'Workspace', keywords: ['company','account'] },\n"
                                                            "  { id: 'users', label: 'Users', description: 'Memberships and roles', icon: '○', group: "
                                                            "'Workspace', keywords: ['people','members','roles'] },\n"
                                                            "  { id: 'seats', label: 'Seat management', description: 'Assignments and availability', icon: "
                                                            "'▦', group: 'Workspace', keywords: ['licenses','assignments'] },\n"
                                                            "  { id: 'reports', label: 'Reports', description: 'Report access and entitlements', icon: '▤', "
                                                            "group: 'Workspace', keywords: ['documents','access'] },\n"
                                                            "  { id: 'access-packages', label: 'Access packages', description: 'Reusable permission bundles', "
                                                            "icon: '◫', group: 'Workspace', keywords: ['permissions','entitlements'] },\n"
                                                            "  { id: 'settings', label: 'Settings', description: 'Workspace configuration', icon: '⚙', group: "
                                                            "'Governance', keywords: ['configuration','rules'] },\n"
                                                            "  { id: 'approvals', label: 'Pending approvals', description: 'Review governed proposals', icon: "
                                                            "'✓', group: 'Governance', keywords: ['proposals','review'] },\n"
                                                            "  { id: 'audit', label: 'Audit history', description: 'Trace decisions and outcomes', icon: '◷', "
                                                            "group: 'Governance', keywords: ['history','events','receipts'] }\n"
                                                            '];\n'
                                                            '\n'
                                                            'export function navigationItem(id: ShellSectionId): ShellNavigationItem {\n'
                                                            '  const item = SHELL_NAVIGATION.find((candidate) => candidate.id === id);\n'
                                                            '  if (!item) throw new Error(`Unknown shell section: ${id}`);\n'
                                                            '  return item;\n'
                                                            '}\n',
 'frontend/src/app/layout/shell/shell-state.service.spec.ts': "import { TestBed } from '@angular/core/testing';\n"
                                                              "import { beforeEach, describe, expect, it } from 'vitest';\n"
                                                              "import { ShellStateService } from './shell-state.service';\n"
                                                              '\n'
                                                              "describe('ShellStateService', () => {\n"
                                                              '  beforeEach(() => { localStorage.clear(); TestBed.configureTestingModule({}); });\n'
                                                              "  it('clamps and persists the assistant width', () => {\n"
                                                              '    const service = TestBed.inject(ShellStateService);\n'
                                                              '    service.setAssistantWidth(900);\n'
                                                              '    TestBed.tick();\n'
                                                              '    expect(service.assistantWidth()).toBe(608);\n'
                                                              "    expect(localStorage.getItem('dbmr-workplace-assistant-width')).toBe('608');\n"
                                                              '  });\n'
                                                              "  it('updates the active workspace section', () => {\n"
                                                              '    const service = TestBed.inject(ShellStateService);\n'
                                                              "    service.selectSection('users');\n"
                                                              "    expect(service.activeSection()).toBe('users');\n"
                                                              '  });\n'
                                                              '});\n',
 'frontend/src/app/layout/shell/shell-state.service.ts': "import { DOCUMENT } from '@angular/common';\n"
                                                         "import { computed, DestroyRef, effect, inject, Injectable, signal } from '@angular/core';\n"
                                                         "import type { ShellSectionId } from './shell-navigation.model';\n"
                                                         '\n'
                                                         "const ASSISTANT_WIDTH_KEY = 'dbmr-workplace-assistant-width';\n"
                                                         "const ASSISTANT_OPEN_KEY = 'dbmr-workplace-assistant-open';\n"
                                                         'const MIN_ASSISTANT_WIDTH = 352;\n'
                                                         'const MAX_ASSISTANT_WIDTH = 608;\n'
                                                         'const DEFAULT_ASSISTANT_WIDTH = 448;\n'
                                                         '\n'
                                                         "@Injectable({ providedIn: 'root' })\n"
                                                         'export class ShellStateService {\n'
                                                         '  private readonly document = inject(DOCUMENT);\n'
                                                         '  private readonly destroyRef = inject(DestroyRef);\n'
                                                         "  private readonly compactQuery = this.document.defaultView?.matchMedia?.('(max-width: 47.99rem)') "
                                                         '?? null;\n'
                                                         "  private readonly narrowQuery = this.document.defaultView?.matchMedia?.('(max-width: 73.99rem)') ?? "
                                                         'null;\n'
                                                         "  private readonly activeSectionState = signal<ShellSectionId>('home');\n"
                                                         '  private readonly sidebarOpenState = signal(false);\n'
                                                         '  private readonly assistantOpenState = signal(this.readBoolean(ASSISTANT_OPEN_KEY, '
                                                         '!(this.compactQuery?.matches ?? false)));\n'
                                                         '  private readonly assistantWidthState = signal(this.readWidth());\n'
                                                         '  private readonly compactState = signal(this.compactQuery?.matches ?? false);\n'
                                                         '  private readonly narrowState = signal(this.narrowQuery?.matches ?? false);\n'
                                                         '\n'
                                                         '  readonly activeSection = this.activeSectionState.asReadonly();\n'
                                                         '  readonly sidebarOpen = this.sidebarOpenState.asReadonly();\n'
                                                         '  readonly assistantOpen = this.assistantOpenState.asReadonly();\n'
                                                         '  readonly assistantWidth = this.assistantWidthState.asReadonly();\n'
                                                         '  readonly isCompact = this.compactState.asReadonly();\n'
                                                         '  readonly isNarrow = this.narrowState.asReadonly();\n'
                                                         '  readonly assistantOverlay = computed(() => this.isNarrow());\n'
                                                         '\n'
                                                         '  constructor() {\n'
                                                         '    const onCompact = (event: MediaQueryListEvent): void => {\n'
                                                         '      this.compactState.set(event.matches);\n'
                                                         '      if (!event.matches) this.sidebarOpenState.set(false);\n'
                                                         '    };\n'
                                                         '    const onNarrow = (event: MediaQueryListEvent): void => this.narrowState.set(event.matches);\n'
                                                         "    this.compactQuery?.addEventListener('change', onCompact);\n"
                                                         "    this.narrowQuery?.addEventListener('change', onNarrow);\n"
                                                         '    this.destroyRef.onDestroy(() => {\n'
                                                         "      this.compactQuery?.removeEventListener('change', onCompact);\n"
                                                         "      this.narrowQuery?.removeEventListener('change', onNarrow);\n"
                                                         '    });\n'
                                                         '    effect(() => this.writeStorage(ASSISTANT_WIDTH_KEY, String(this.assistantWidth())));\n'
                                                         '    effect(() => this.writeStorage(ASSISTANT_OPEN_KEY, String(this.assistantOpen())));\n'
                                                         '  }\n'
                                                         '\n'
                                                         '  selectSection(section: ShellSectionId): void {\n'
                                                         '    this.activeSectionState.set(section);\n'
                                                         '    if (this.isCompact()) this.sidebarOpenState.set(false);\n'
                                                         '  }\n'
                                                         '  openSidebar(): void { this.sidebarOpenState.set(true); }\n'
                                                         '  closeSidebar(): void { this.sidebarOpenState.set(false); }\n'
                                                         '  toggleSidebar(): void { this.sidebarOpenState.update((open) => !open); }\n'
                                                         '  openAssistant(): void { this.assistantOpenState.set(true); }\n'
                                                         '  closeAssistant(): void { this.assistantOpenState.set(false); }\n'
                                                         '  toggleAssistant(): void { this.assistantOpenState.update((open) => !open); }\n'
                                                         '  setAssistantWidth(width: number): void {\n'
                                                         '    this.assistantWidthState.set(Math.min(MAX_ASSISTANT_WIDTH, Math.max(MIN_ASSISTANT_WIDTH, '
                                                         'Math.round(width))));\n'
                                                         '  }\n'
                                                         '  closeOverlays(): void {\n'
                                                         '    if (this.isCompact()) this.closeSidebar();\n'
                                                         '    if (this.assistantOverlay()) this.closeAssistant();\n'
                                                         '  }\n'
                                                         '\n'
                                                         '  private readWidth(): number {\n'
                                                         '    const parsed = Number(this.readStorage(ASSISTANT_WIDTH_KEY));\n'
                                                         '    return Number.isFinite(parsed) ? Math.min(MAX_ASSISTANT_WIDTH, Math.max(MIN_ASSISTANT_WIDTH, '
                                                         'parsed)) : DEFAULT_ASSISTANT_WIDTH;\n'
                                                         '  }\n'
                                                         '  private readBoolean(key: string, fallback: boolean): boolean {\n'
                                                         '    const value = this.readStorage(key);\n'
                                                         "    return value === 'true' ? true : value === 'false' ? false : fallback;\n"
                                                         '  }\n'
                                                         '  private readStorage(key: string): string | null {\n'
                                                         '    try { return this.document.defaultView?.localStorage.getItem(key) ?? null; } catch { return '
                                                         'null; }\n'
                                                         '  }\n'
                                                         '  private writeStorage(key: string, value: string): void {\n'
                                                         '    try { this.document.defaultView?.localStorage.setItem(key, value); } catch { /* unavailable '
                                                         'storage is non-fatal */ }\n'
                                                         '  }\n'
                                                         '}\n',
 'frontend/src/app/layout/workspace/workspace-dashboard.component.html': "@if (section === 'home') {\n"
                                                                         '  <div class="workspace-home">\n'
                                                                         '    <section class="workspace-hero">\n'
                                                                         '      <app-ui-badge tone="warning">Governed workplace agent</app-ui-badge>\n'
                                                                         "      <h1>Let's get to work.</h1>\n"
                                                                         '      <p>Explore workplace resources, review governed actions, or open Ask AI for '
                                                                         'natural-language assistance.</p>\n'
                                                                         '      <div class="workspace-search">\n'
                                                                         '        <app-ui-input label="Search workspace" type="search" '
                                                                         'placeholder="Organizations, users, reports, settings…" [(value)]="searchValue" />\n'
                                                                         '        <kbd>Ctrl K</kbd>\n'
                                                                         '      </div>\n'
                                                                         '    </section>\n'
                                                                         '\n'
                                                                         '    <section class="workspace-section" aria-labelledby="resources-title">\n'
                                                                         '      <div class="workspace-section__heading"><div><span>Workspace</span><h2 '
                                                                         'id="resources-title">Resources</h2></div></div>\n'
                                                                         '      <div class="resource-grid">\n'
                                                                         '        @for (item of visibleResources; track item.id) {\n'
                                                                         '          <app-ui-action-surface [heading]="item.label" '
                                                                         '[description]="item.description" [icon]="item.icon" '
                                                                         '(activated)="navigate.emit(item.id)" />\n'
                                                                         '        } @empty {\n'
                                                                         '          <p class="workspace-empty">No workspace resources match your search.</p>\n'
                                                                         '        }\n'
                                                                         '      </div>\n'
                                                                         '    </section>\n'
                                                                         '\n'
                                                                         '    <app-ui-callout tone="info" title="Backend-owned governance">\n'
                                                                         '      Risk, approval policy, resource versions, execution, reconciliation, and '
                                                                         'rollback remain enforced by the existing backend.\n'
                                                                         '    </app-ui-callout>\n'
                                                                         '  </div>\n'
                                                                         '} @else {\n'
                                                                         '  <div class="workspace-page">\n'
                                                                         '    <nav aria-label="Breadcrumb"><button type="button" '
                                                                         '(click)="navigate.emit(\'home\')">Workspace home</button><span '
                                                                         'aria-hidden="true">›</span><span>{{ current.label }}</span></nav>\n'
                                                                         '    <header>\n'
                                                                         '      <div><span class="workspace-eyebrow">{{ current.group }}</span><h1>{{ '
                                                                         'current.label }}</h1><p>{{ current.description }}</p></div>\n'
                                                                         '      <app-ui-button variant="outline" (pressed)="askAi.emit()">Ask AI about '
                                                                         'this</app-ui-button>\n'
                                                                         '    </header>\n'
                                                                         '    <app-ui-callout tone="info" title="Shell ready">\n'
                                                                         '      This section is structurally complete. Its live data view is connected in the '
                                                                         'dedicated resource-dashboard phase, without duplicating backend rules.\n'
                                                                         '    </app-ui-callout>\n'
                                                                         '    <section class="workspace-section" aria-labelledby="related-title">\n'
                                                                         '      <div class="workspace-section__heading"><div><span>Continue</span><h2 '
                                                                         'id="related-title">Related workspace areas</h2></div></div>\n'
                                                                         '      <div class="resource-grid">\n'
                                                                         '        @for (item of relatedResources; track item.id) {\n'
                                                                         '          <app-ui-action-surface [heading]="item.label" '
                                                                         '[description]="item.description" [icon]="item.icon" '
                                                                         '(activated)="navigate.emit(item.id)" />\n'
                                                                         '        }\n'
                                                                         '      </div>\n'
                                                                         '    </section>\n'
                                                                         '  </div>\n'
                                                                         '}\n',
 'frontend/src/app/layout/workspace/workspace-dashboard.component.scss': ':host { display: block; min-height: 100%; }\n'
                                                                         '.workspace-home, .workspace-page { width: min(100%, 62rem); margin: 0 auto; padding: '
                                                                         'clamp(2rem, 5vw, 4.5rem) clamp(1.25rem, 4vw, 3.5rem); }\n'
                                                                         '.workspace-hero { display: grid; justify-items: center; gap: var(--ui-space-4); '
                                                                         'margin-bottom: var(--ui-space-12); text-align: center; }\n'
                                                                         '.workspace-hero h1, .workspace-page h1 { margin: 0; color: var(--ui-text-primary); '
                                                                         'font-size: var(--ui-text-2xl); line-height: var(--ui-leading-tight); }\n'
                                                                         '.workspace-hero > p { max-width: 38rem; margin: 0; color: var(--ui-text-secondary); '
                                                                         'line-height: var(--ui-leading-relaxed); }\n'
                                                                         '.workspace-search { position: relative; width: min(100%, 38rem); margin-top: '
                                                                         'var(--ui-space-3); border: 6px solid color-mix(in srgb, var(--ui-border-subtle) 38%, '
                                                                         'transparent); border-radius: var(--ui-radius-xl); }\n'
                                                                         '.workspace-search app-ui-input { display: block; }\n'
                                                                         '.workspace-search kbd { position: absolute; right: var(--ui-space-3); bottom: '
                                                                         'var(--ui-space-3); border: 1px solid var(--ui-border-subtle); border-radius: '
                                                                         'var(--ui-radius-xs); background: var(--ui-surface-muted); color: '
                                                                         'var(--ui-text-muted); padding: 0.1rem 0.35rem; font: inherit; font-size: '
                                                                         'var(--ui-text-xs); }\n'
                                                                         '.workspace-section { margin-top: var(--ui-space-10); }\n'
                                                                         '.workspace-section__heading { display: flex; align-items: end; justify-content: '
                                                                         'space-between; margin-bottom: var(--ui-space-4); }\n'
                                                                         '.workspace-section__heading span, .workspace-eyebrow { color: var(--ui-text-muted); '
                                                                         'font-size: var(--ui-text-xs); font-weight: var(--ui-weight-semibold); '
                                                                         'letter-spacing: 0.06em; text-transform: uppercase; }\n'
                                                                         '.workspace-section h2 { margin: var(--ui-space-1) 0 0; font-size: var(--ui-text-xl); '
                                                                         '}\n'
                                                                         '.resource-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); '
                                                                         'gap: var(--ui-space-3); }\n'
                                                                         '.workspace-empty { grid-column: 1 / -1; color: var(--ui-text-secondary); text-align: '
                                                                         'center; }\n'
                                                                         '.workspace-page > nav { display: flex; align-items: center; gap: var(--ui-space-2); '
                                                                         'color: var(--ui-text-muted); font-size: var(--ui-text-sm); }\n'
                                                                         '.workspace-page > nav button { border: 0; background: transparent; color: '
                                                                         'var(--ui-text-link); padding: 0; cursor: pointer; }\n'
                                                                         '.workspace-page > header { display: flex; align-items: start; justify-content: '
                                                                         'space-between; gap: var(--ui-space-6); margin: var(--ui-space-8) 0; }\n'
                                                                         '.workspace-page > header p { max-width: 34rem; margin: var(--ui-space-3) 0 0; color: '
                                                                         'var(--ui-text-secondary); line-height: var(--ui-leading-relaxed); }\n'
                                                                         '@media (max-width: 47.99rem) {\n'
                                                                         '  .workspace-home, .workspace-page { padding: var(--ui-space-8) var(--ui-space-4); '
                                                                         '}\n'
                                                                         '  .resource-grid { grid-template-columns: 1fr; }\n'
                                                                         '  .workspace-page > header { flex-direction: column; }\n'
                                                                         '}\n',
 'frontend/src/app/layout/workspace/workspace-dashboard.component.ts': 'import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '
                                                                       "'@angular/core';\n"
                                                                       'import { UiActionSurfaceComponent, UiBadgeComponent, UiButtonComponent, '
                                                                       "UiCalloutComponent, UiInputComponent } from '../../shared/ui';\n"
                                                                       'import { navigationItem, SHELL_NAVIGATION, type ShellNavigationItem, type '
                                                                       "ShellSectionId } from '../shell/shell-navigation.model';\n"
                                                                       '\n'
                                                                       '@Component({\n'
                                                                       "  selector: 'app-workspace-dashboard',\n"
                                                                       '  standalone: true,\n'
                                                                       '  imports: [UiActionSurfaceComponent, UiBadgeComponent, UiButtonComponent, '
                                                                       'UiCalloutComponent, UiInputComponent],\n'
                                                                       '  changeDetection: ChangeDetectionStrategy.OnPush,\n'
                                                                       "  templateUrl: './workspace-dashboard.component.html',\n"
                                                                       "  styleUrl: './workspace-dashboard.component.scss'\n"
                                                                       '})\n'
                                                                       'export class WorkspaceDashboardComponent {\n'
                                                                       "  @Input({ required: true }) section: ShellSectionId = 'home';\n"
                                                                       '  @Output() readonly navigate = new EventEmitter<ShellSectionId>();\n'
                                                                       '  @Output() readonly askAi = new EventEmitter<void>();\n'
                                                                       "  searchValue = '';\n"
                                                                       '\n'
                                                                       '  get current(): ShellNavigationItem { return navigationItem(this.section); }\n'
                                                                       '  get visibleResources(): readonly ShellNavigationItem[] {\n'
                                                                       '    const term = this.searchValue.trim().toLowerCase();\n'
                                                                       "    return SHELL_NAVIGATION.filter((item) => item.id !== 'home' && (!term || "
                                                                       '[item.label,item.description,...item.keywords].some((value) => '
                                                                       'value.toLowerCase().includes(term))));\n'
                                                                       '  }\n'
                                                                       '  get relatedResources(): readonly ShellNavigationItem[] {\n'
                                                                       "    return SHELL_NAVIGATION.filter((item) => item.id !== 'home' && item.id !== "
                                                                       'this.section).slice(0, 4);\n'
                                                                       '  }\n'
                                                                       '}\n',
 'frontend/src/app/shared/ui/ui-action-surface/ui-action-surface.component.html': '<button\n'
                                                                                  '  type="button"\n'
                                                                                  '  class="action-surface"\n'
                                                                                  '  [class.action-surface--selected]="selected"\n'
                                                                                  '  [disabled]="disabled"\n'
                                                                                  '  [attr.aria-pressed]="selected ? true : null"\n'
                                                                                  '  (click)="activated.emit()"\n'
                                                                                  '>\n'
                                                                                  '  <span class="action-surface__icon" aria-hidden="true">{{ icon }}</span>\n'
                                                                                  '  <span class="action-surface__body">\n'
                                                                                  '    <strong>{{ heading }}</strong>\n'
                                                                                  '    @if (description) { <span>{{ description }}</span> }\n'
                                                                                  '    @if (meta) { <small>{{ meta }}</small> }\n'
                                                                                  '  </span>\n'
                                                                                  '  <span class="action-surface__arrow" aria-hidden="true">›</span>\n'
                                                                                  '</button>\n',
 'frontend/src/app/shared/ui/ui-action-surface/ui-action-surface.component.scss': ':host { display: block; }\n'
                                                                                  '.action-surface {\n'
                                                                                  '  display: grid;\n'
                                                                                  '  width: 100%;\n'
                                                                                  '  min-height: 5.25rem;\n'
                                                                                  '  grid-template-columns: auto minmax(0, 1fr) auto;\n'
                                                                                  '  align-items: center;\n'
                                                                                  '  gap: var(--ui-space-3);\n'
                                                                                  '  border: 1px solid var(--ui-border-subtle);\n'
                                                                                  '  border-radius: var(--ui-radius-lg);\n'
                                                                                  '  background: var(--ui-surface-base);\n'
                                                                                  '  color: var(--ui-text-primary);\n'
                                                                                  '  padding: var(--ui-space-4);\n'
                                                                                  '  text-align: left;\n'
                                                                                  '  cursor: pointer;\n'
                                                                                  '  transition: border-color var(--ui-duration-fast) var(--ui-ease-standard), '
                                                                                  'box-shadow var(--ui-duration-fast) var(--ui-ease-standard), transform '
                                                                                  'var(--ui-duration-fast) var(--ui-ease-standard), background '
                                                                                  'var(--ui-duration-fast) var(--ui-ease-standard);\n'
                                                                                  '}\n'
                                                                                  '.action-surface:hover:not(:disabled) { border-color: '
                                                                                  'var(--ui-border-default); box-shadow: var(--ui-shadow-sm); transform: '
                                                                                  'translateY(-1px); }\n'
                                                                                  '.action-surface:active:not(:disabled) { transform: translateY(0); }\n'
                                                                                  '.action-surface--selected { border-color: var(--ui-brand-500); background: '
                                                                                  'var(--ui-surface-selected); }\n'
                                                                                  '.action-surface:disabled { cursor: not-allowed; opacity: 0.55; }\n'
                                                                                  '.action-surface__icon { display: grid; width: 2.25rem; height: 2.25rem; '
                                                                                  'place-items: center; border-radius: var(--ui-radius-md); background: '
                                                                                  'var(--ui-surface-muted); color: var(--ui-text-secondary); font-size: '
                                                                                  'var(--ui-text-lg); }\n'
                                                                                  '.action-surface__body { display: grid; min-width: 0; gap: '
                                                                                  'var(--ui-space-1); }\n'
                                                                                  '.action-surface__body strong { font-size: var(--ui-text-md); }\n'
                                                                                  '.action-surface__body span { color: var(--ui-text-secondary); font-size: '
                                                                                  'var(--ui-text-sm); line-height: var(--ui-leading-normal); }\n'
                                                                                  '.action-surface__body small { color: var(--ui-text-muted); font-size: '
                                                                                  'var(--ui-text-xs); }\n'
                                                                                  '.action-surface__arrow { color: var(--ui-text-muted); font-size: '
                                                                                  'var(--ui-text-xl); }\n',
 'frontend/src/app/shared/ui/ui-action-surface/ui-action-surface.component.spec.ts': "import { TestBed } from '@angular/core/testing';\n"
                                                                                     "import { describe, expect, it, vi } from 'vitest';\n"
                                                                                     'import { UiActionSurfaceComponent } from '
                                                                                     "'./ui-action-surface.component';\n"
                                                                                     '\n'
                                                                                     "describe('UiActionSurfaceComponent', () => {\n"
                                                                                     "  it('uses native button keyboard semantics and emits activation', async "
                                                                                     '() => {\n'
                                                                                     '    await TestBed.configureTestingModule({ imports: '
                                                                                     '[UiActionSurfaceComponent] }).compileComponents();\n'
                                                                                     '    const fixture = TestBed.createComponent(UiActionSurfaceComponent);\n'
                                                                                     "    fixture.componentInstance.heading = 'Users';\n"
                                                                                     '    const activated = vi.fn();\n'
                                                                                     '    fixture.componentInstance.activated.subscribe(activated);\n'
                                                                                     '    fixture.detectChanges();\n'
                                                                                      "    const button = (fixture.nativeElement as HTMLElement).querySelector('button') as "
                                                                                      'HTMLButtonElement;\n'
                                                                                     '    button.click();\n'
                                                                                     '    expect(activated).toHaveBeenCalledOnce();\n'
                                                                                     "    expect(button.type).toBe('button');\n"
                                                                                     '  });\n'
                                                                                     '});\n',
 'frontend/src/app/shared/ui/ui-action-surface/ui-action-surface.component.ts': 'import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } '
                                                                                "from '@angular/core';\n"
                                                                                '\n'
                                                                                '@Component({\n'
                                                                                "  selector: 'app-ui-action-surface',\n"
                                                                                '  standalone: true,\n'
                                                                                '  changeDetection: ChangeDetectionStrategy.OnPush,\n'
                                                                                "  templateUrl: './ui-action-surface.component.html',\n"
                                                                                "  styleUrl: './ui-action-surface.component.scss'\n"
                                                                                '})\n'
                                                                                'export class UiActionSurfaceComponent {\n'
                                                                                "  @Input({ required: true }) heading = '';\n"
                                                                                "  @Input() description = '';\n"
                                                                                "  @Input() meta = '';\n"
                                                                                "  @Input() icon = '◇';\n"
                                                                                '  @Input() selected = false;\n'
                                                                                '  @Input() disabled = false;\n'
                                                                                '  @Output() readonly activated = new EventEmitter<void>();\n'
                                                                                '}\n',
 'frontend/src/app/shared/ui/ui-textarea/ui-textarea.component.spec.ts': "import { Component } from '@angular/core';\n"
                                                                         "import { TestBed } from '@angular/core/testing';\n"
                                                                         "import { FormControl, ReactiveFormsModule } from '@angular/forms';\n"
                                                                         "import { describe, expect, it } from 'vitest';\n"
                                                                         "import { UiTextareaComponent } from './ui-textarea.component';\n"
                                                                         '\n'
                                                                         '@Component({\n'
                                                                         '  standalone: true,\n'
                                                                         '  imports: [ReactiveFormsModule, UiTextareaComponent],\n'
                                                                         '  template: \'<app-ui-textarea label="Message" [formControl]="control" />\'\n'
                                                                         '})\n'
                                                                         "class TextareaHostComponent { readonly control = new FormControl('Initial note', { "
                                                                         'nonNullable: true }); }\n'
                                                                         '\n'
                                                                         "describe('UiTextareaComponent', () => {\n"
                                                                         "  it('integrates with reactive forms and marks the native control disabled', async "
                                                                         '() => {\n'
                                                                         '    await TestBed.configureTestingModule({ imports: [TextareaHostComponent] '
                                                                         '}).compileComponents();\n'
                                                                         '    const fixture = TestBed.createComponent(TextareaHostComponent);\n'
                                                                         '    fixture.detectChanges();\n'
                                                                          "    const textarea = (fixture.nativeElement as HTMLElement).querySelector('textarea') as "
                                                                          'HTMLTextAreaElement;\n'
                                                                         "    expect(textarea.value).toBe('Initial note');\n"
                                                                         "    textarea.value = 'Updated note';\n"
                                                                         "    textarea.dispatchEvent(new Event('input'));\n"
                                                                         "    expect(fixture.componentInstance.control.value).toBe('Updated note');\n"
                                                                         '    fixture.componentInstance.control.disable();\n'
                                                                         '    fixture.detectChanges();\n'
                                                                         '    expect(textarea.disabled).toBe(true);\n'
                                                                         '  });\n'
                                                                         '});\n',
 'scripts/validate_angular_phase3.py': '#!/usr/bin/env python3\n'
                                       'from __future__ import annotations\n'
                                       'import argparse, json\n'
                                       'from pathlib import Path\n'
                                       '\n'
                                       'REQUIRED=(\n'
                                       " 'frontend/src/app/layout/app-shell/app-shell.component.ts',\n"
                                       " 'frontend/src/app/layout/global-header/global-header.component.ts',\n"
                                       " 'frontend/src/app/layout/primary-sidebar/primary-sidebar.component.ts',\n"
                                       " 'frontend/src/app/layout/workspace/workspace-dashboard.component.ts',\n"
                                       " 'frontend/src/app/layout/assistant-panel/assistant-panel.component.ts',\n"
                                       " 'frontend/src/app/layout/assistant-resize-handle/assistant-resize-handle.component.ts',\n"
                                       " 'frontend/src/app/layout/shell/shell-state.service.ts',\n"
                                       " 'frontend/src/app/layout/shell/shell-navigation.model.ts',\n"
                                       " 'frontend/docs/PHASE_3_SHELL.md',\n"
                                       ')\n'
                                       'def validate(repo:Path)->list[str]:\n'
                                       ' errors=[]\n'
                                       ' for rel in REQUIRED:\n'
                                       "  if not (repo/rel).is_file(): errors.append(f'{rel}: missing')\n"
                                       " package=json.loads((repo/'frontend/package.json').read_text(encoding='utf-8'))\n"
                                       " if 'validate:phase3' not in package.get('scripts',{}): errors.append('package.json: validate:phase3 missing')\n"
                                       " app=(repo/'frontend/src/app/app.component.ts').read_text(encoding='utf-8')\n"
                                       " if 'AppShellComponent' not in app: errors.append('AppComponent does not delegate to AppShellComponent')\n"
                                       " shell=(repo/'frontend/src/app/layout/app-shell/app-shell.component.html').read_text(encoding='utf-8')\n"
                                       ' for required in '
                                       "('app-global-header','app-primary-sidebar','app-workspace-dashboard','app-assistant-panel','app-assistant-resize-handle'):\n"
                                       "  if required not in shell: errors.append(f'app shell missing {required}')\n"
                                       " state=(repo/'frontend/src/app/layout/shell/shell-state.service.ts').read_text(encoding='utf-8')\n"
                                       " for required in ('assistantWidth','localStorage','matchMedia','selectSection','setAssistantWidth'):\n"
                                       "  if required not in state: errors.append(f'ShellStateService missing {required}')\n"
                                       " nav=(repo/'frontend/src/app/layout/shell/shell-navigation.model.ts').read_text(encoding='utf-8')\n"
                                       " for required in ('organizations','users','seats','reports','access-packages','settings','approvals','audit'):\n"
                                       '  if f"\'{required}\'" not in nav: errors.append(f\'navigation missing {required}\')\n'
                                       " css=(repo/'frontend/src/app/layout/app-shell/app-shell.component.scss').read_text(encoding='utf-8')\n"
                                       " for breakpoint in ('73.99rem','47.99rem'):\n"
                                       "  if breakpoint not in css: errors.append(f'app shell missing responsive breakpoint {breakpoint}')\n"
                                       " e2e=(repo/'frontend/e2e/foundation.spec.ts').read_text(encoding='utf-8')\n"
                                       " for scenario in ('complete workplace shell','responsive Ask AI panel','persists the dark theme'):\n"
                                       "  if scenario not in e2e: errors.append(f'Playwright missing {scenario}')\n"
                                       " visible='\\n'.join(path.read_text(encoding='utf-8') for path in (repo/'frontend/src/app').rglob('*.html'))\n"
                                       " for forbidden in ('Cloudflare','currentUser.userId()','organizationId','chain-of-thought'):\n"
                                       "  if forbidden in visible: errors.append(f'visible shell contains forbidden value: {forbidden}')\n"
                                       ' return errors\n'
                                       '\n'
                                       'def main()->int:\n'
                                       ' '
                                       "parser=argparse.ArgumentParser();parser.add_argument('--repo',default='.');args=parser.parse_args();errors=validate(Path(args.repo).resolve())\n"
                                       ' if errors:\n'
                                       "  print('Angular Phase 3 validation failed:');[print(f'- {e}') for e in errors];return 1\n"
                                       " print('Angular Phase 3 shell is valid: responsive navigation, workspace, Ask AI panel, resizing, and hardening checks "
                                       "pass.');return 0\n"
                                       "if __name__=='__main__': raise SystemExit(main())\n",
 'tests/test_angular_phase3.py': 'from pathlib import Path\n'
                                 'from scripts.validate_angular_phase3 import validate\n'
                                 'ROOT=Path(__file__).resolve().parents[1]\n'
                                 'def test_phase3_shell_contract()->None: assert validate(ROOT)==[]\n'
                                 'def test_phase3_does_not_fake_agent_execution()->None:\n'
                                 " text='\\n'.join(path.read_text(encoding='utf-8').lower() for path in (ROOT/'frontend/src/app/layout').rglob('*.html'))\n"
                                 " assert 'execution succeeded' not in text\n"
                                 " assert 'fake reasoning' not in text\n"}
APPENDS={'APPLY_AND_VALIDATE.md': '\n'
                          '\n'
                          '<!-- ANGULAR_FRONTEND_PHASE_3_VALIDATION -->\n'
                          '## Angular frontend Phase 3 validation\n'
                          '\n'
                          '```powershell\n'
                          'python scripts/validate_angular_phase2.py --repo .\n'
                          'python scripts/validate_angular_phase3.py --repo .\n'
                          'pytest -q tests/test_angular_phase2.py tests/test_angular_phase3.py\n'
                          'Set-Location frontend\n'
                          'npm run validate:phase3\n'
                          'npm run e2e\n'
                          'Set-Location ..\n'
                          'pytest -q\n'
                          'git diff --check\n'
                          '```\n',
 'README.md': '\n'
              '\n'
              '<!-- ANGULAR_FRONTEND_PHASE_3_SHELL -->\n'
              '## Angular frontend Phase 3 shell\n'
              '\n'
              'The design system is hardened for contrast, pre-bootstrap theming, Angular forms, and native interactive semantics. The frontend now presents a '
              'responsive workplace shell with searchable navigation, a functional workspace, and a collapsible/resizable Ask AI panel. See '
              '`frontend/docs/PHASE_3_SHELL.md`.\n',
 'frontend/README.md': '\n'
                       '\n'
                       '<!-- ANGULAR_FRONTEND_PHASE_3_SHELL -->\n'
                       '## Phase 3 workplace shell\n'
                       '\n'
                       'The Angular app now uses the production-shaped three-panel workplace shell. Phase 2 hardening adds contrast validation, pre-bootstrap '
                       'theming, ControlValueAccessor form controls, and native action surfaces.\n'}
REQUIRED=(
 'frontend/package-lock.json',
 'frontend/proxy.conf.json',
 'scripts/validate_frontend_contracts.py',
 'scripts/validate_angular_phase1.py',
 'scripts/validate_angular_phase2.py',
 'frontend/src/app/core/api/workplace-agent-api.service.ts',
)

def run(repo:Path,*args:str,check:bool=True,cwd:Path|None=None)->subprocess.CompletedProcess[str]:
 return subprocess.run(list(args),cwd=cwd or repo,check=check,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
def git(repo:Path,*args:str)->str:return run(repo,'git',*args).stdout.strip()
def digest(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def npm_command()->str:return 'npm.cmd' if os.name=='nt' else 'npm'
def normalized_origin(origin:str)->str:return origin.removesuffix('.git').replace('git@github.com:','https://github.com/').rstrip('/')

def verify_repo(repo:Path)->None:
 root=Path(git(repo,'rev-parse','--show-toplevel')).resolve()
 if root!=repo.resolve():raise RuntimeError('Run from the repository root or pass --repo.')
 branch=git(repo,'branch','--show-current')
 if branch!=EXPECTED_BRANCH:raise RuntimeError(f'Expected branch {EXPECTED_BRANCH}, found {branch}.')
 head=git(repo,'rev-parse','HEAD')
 if head!=EXPECTED_HEAD:raise RuntimeError(f'Expected HEAD {EXPECTED_HEAD}, found {head}.')
 origin=normalized_origin(git(repo,'remote','get-url','origin'))
 if not origin.endswith(EXPECTED_REPOSITORY):raise RuntimeError(f'Unexpected origin: {origin}')
 if git(repo,'status','--porcelain','--untracked-files=no'):raise RuntimeError('Tracked working tree must be clean before applying Phase 3.')
 for rel in REQUIRED:
  if not (repo/rel).is_file():raise RuntimeError(f'Required prior-phase file is missing: {rel}')
 for rel,expected in EXPECTED_HASHES.items():
  path=repo/rel
  if not path.is_file():raise RuntimeError(f'Expected Phase 2 file is missing: {rel}')
  actual=digest(path)
  if actual!=expected:raise RuntimeError(f'Phase 2 source drift in {rel}: expected {expected}, found {actual}')
 for rel in NEW_FILES:
  if (repo/rel).exists():raise RuntimeError(f'Phase 3 target already exists: {rel}')
 for rel,addition in APPENDS.items():
  path=repo/rel
  if not path.is_file():raise RuntimeError(f'Append target is missing: {rel}')
  marker=next(line for line in addition.splitlines() if line.startswith('<!--'))
  if marker in path.read_text(encoding='utf-8'):raise RuntimeError(f'Phase 3 marker already exists in {rel}')

def write_atomic(path:Path,content:str)->None:
 path.parent.mkdir(parents=True,exist_ok=True)
 temp=path.with_name(path.name+'.phase3.tmp')
 temp.write_text(content.rstrip()+'\n',encoding='utf-8',newline='\n')
 os.replace(temp,path)

def apply(repo:Path,*,skip_node:bool=False,skip_browser_tests:bool=False,skip_full_backend:bool=False)->None:
 created=[];backups={}
 try:
  for rel,content in REPLACEMENTS.items():
   path=repo/rel;backups[path]=path.read_bytes();write_atomic(path,content)
  for rel,content in NEW_FILES.items():
   path=repo/rel;write_atomic(path,content);created.append(path)
  for rel,addition in APPENDS.items():
   path=repo/rel;backups[path]=path.read_bytes();write_atomic(path,path.read_text(encoding='utf-8').rstrip()+addition)
  checks=[
   (sys.executable,'scripts/validate_frontend_contracts.py','--repo','.'),
   (sys.executable,'scripts/validate_angular_phase1.py','--repo','.'),
   (sys.executable,'scripts/validate_angular_phase2.py','--repo','.'),
   (sys.executable,'scripts/validate_angular_phase3.py','--repo','.'),
   (sys.executable,'-m','pytest','-q','tests/test_frontend_contracts.py','tests/test_angular_phase1_foundation.py','tests/test_angular_phase2.py','tests/test_angular_phase3.py'),
   (sys.executable,'-m','compileall','-q','scripts','tests'),
   ('git','diff','--check'),
  ]
  for command in checks:
   result=run(repo,*command,check=False)
   if result.returncode!=0:raise RuntimeError('Validation failed: '+' '.join(command)+'\n'+result.stdout)
  if not skip_node:
   frontend=repo/'frontend';npm=npm_command()
   if not (frontend/'node_modules').is_dir():
    result=run(repo,npm,'install',check=False,cwd=frontend)
    if result.returncode!=0:raise RuntimeError('npm install failed:\n'+result.stdout)
   result=run(repo,npm,'run','validate:phase3',check=False,cwd=frontend)
   if result.returncode!=0:raise RuntimeError('Angular Phase 3 validation failed:\n'+result.stdout)
   if not skip_browser_tests:
    result=run(repo,npm,'run','e2e',check=False,cwd=frontend)
    if result.returncode!=0:raise RuntimeError('Playwright browser tests failed:\n'+result.stdout)
  if not skip_full_backend:
   result=run(repo,sys.executable,'-m','pytest','-q',check=False)
   if result.returncode!=0:raise RuntimeError('Full backend regression suite failed:\n'+result.stdout)
 except Exception:
  for path,content in backups.items():
   path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
  for path in reversed(created):
   if path.exists():path.unlink()
  for directory in sorted({path.parent for path in created},key=lambda value:len(value.parts),reverse=True):
   try:directory.rmdir()
   except OSError:pass
  for temp in repo.rglob('*.phase3.tmp'):
   try:temp.unlink()
   except OSError:pass
  raise

def main()->int:
 parser=argparse.ArgumentParser()
 parser.add_argument('--repo',default='.')
 parser.add_argument('--skip-node',action='store_true',help='Skip Angular validation. Use only for applicator development.')
 parser.add_argument('--skip-browser-tests',action='store_true',help='Skip Playwright execution. Not recommended for final acceptance.')
 parser.add_argument('--skip-full-backend',action='store_true',help='Skip the complete backend test suite. Not recommended for final acceptance.')
 args=parser.parse_args();repo=Path(args.repo).resolve();verify_repo(repo)
 apply(repo,skip_node=args.skip_node,skip_browser_tests=args.skip_browser_tests,skip_full_backend=args.skip_full_backend)
 print('Applied Phase 2 hardening and Angular Phase 3 workplace shell.')
 print(f'Baseline: {EXPECTED_HEAD}')
 print(f'Replaced {len(REPLACEMENTS)} files, created {len(NEW_FILES)} files, and updated {len(APPENDS)} documents.')
 print('No files were staged, committed, or pushed.')
 return 0
if __name__=='__main__':raise SystemExit(main())
