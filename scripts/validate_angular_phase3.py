#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

REQUIRED=(
 'frontend/src/app/layout/app-shell/app-shell.component.ts',
 'frontend/src/app/layout/global-header/global-header.component.ts',
 'frontend/src/app/layout/primary-sidebar/primary-sidebar.component.ts',
 'frontend/src/app/layout/workspace/workspace-dashboard.component.ts',
 'frontend/src/app/layout/assistant-panel/assistant-panel.component.ts',
 'frontend/src/app/layout/assistant-resize-handle/assistant-resize-handle.component.ts',
 'frontend/src/app/layout/shell/shell-state.service.ts',
 'frontend/src/app/layout/shell/shell-navigation.model.ts',
 'frontend/docs/PHASE_3_SHELL.md',
)
def validate(repo:Path)->list[str]:
 errors=[]
 for rel in REQUIRED:
  if not (repo/rel).is_file(): errors.append(f'{rel}: missing')
 package=json.loads((repo/'frontend/package.json').read_text(encoding='utf-8'))
 if 'validate:phase3' not in package.get('scripts',{}): errors.append('package.json: validate:phase3 missing')
 app=(repo/'frontend/src/app/app.component.ts').read_text(encoding='utf-8')
 if 'AppShellComponent' not in app: errors.append('AppComponent does not delegate to AppShellComponent')
 shell=(repo/'frontend/src/app/layout/app-shell/app-shell.component.html').read_text(encoding='utf-8')
 for required in ('app-global-header','app-primary-sidebar','app-workspace-dashboard','app-assistant-panel','app-assistant-resize-handle'):
  if required not in shell: errors.append(f'app shell missing {required}')
 state=(repo/'frontend/src/app/layout/shell/shell-state.service.ts').read_text(encoding='utf-8')
 for required in ('assistantWidth','localStorage','matchMedia','selectSection','setAssistantWidth'):
  if required not in state: errors.append(f'ShellStateService missing {required}')
 nav=(repo/'frontend/src/app/layout/shell/shell-navigation.model.ts').read_text(encoding='utf-8')
 for required in ('organizations','users','seats','reports','access-packages','settings','approvals','audit'):
  if f"'{required}'" not in nav: errors.append(f'navigation missing {required}')
 css=(repo/'frontend/src/app/layout/app-shell/app-shell.component.scss').read_text(encoding='utf-8')
 for breakpoint in ('73.99rem','47.99rem'):
  if breakpoint not in css: errors.append(f'app shell missing responsive breakpoint {breakpoint}')
 e2e=(repo/'frontend/e2e/foundation.spec.ts').read_text(encoding='utf-8')
 for scenario in ('complete workplace shell','responsive Ask AI panel','persists the dark theme'):
  if scenario not in e2e: errors.append(f'Playwright missing {scenario}')
 visible='\n'.join(path.read_text(encoding='utf-8') for path in (repo/'frontend/src/app').rglob('*.html'))
 for forbidden in ('Cloudflare','currentUser.userId()','organizationId','chain-of-thought'):
  if forbidden in visible: errors.append(f'visible shell contains forbidden value: {forbidden}')
 return errors

def main()->int:
 parser=argparse.ArgumentParser();parser.add_argument('--repo',default='.');args=parser.parse_args();errors=validate(Path(args.repo).resolve())
 if errors:
  print('Angular Phase 3 validation failed:');[print(f'- {e}') for e in errors];return 1
 print('Angular Phase 3 shell is valid: responsive navigation, workspace, Ask AI panel, resizing, and hardening checks pass.');return 0
if __name__=='__main__': raise SystemExit(main())
