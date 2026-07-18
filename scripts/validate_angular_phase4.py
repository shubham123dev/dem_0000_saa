#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

REQUIRED=(
 'frontend/src/app/features/assistant-conversation/agent-conversation.model.ts',
 'frontend/src/app/features/assistant-conversation/agent-response.mapper.ts',
 'frontend/src/app/features/assistant-conversation/agent-conversation.store.ts',
 'frontend/src/app/features/assistant-conversation/assistant-composer/assistant-composer.component.ts',
 'frontend/src/app/features/assistant-conversation/assistant-message/assistant-message.component.ts',
 'frontend/src/app/features/assistant-conversation/assistant-proposal-card/assistant-proposal-card.component.ts',
 'frontend/e2e/assistant-conversation.spec.ts',
 'frontend/docs/PHASE_4_CONVERSATION.md',
 'frontend/docs/PHASE_4_ACCEPTANCE.md',
)

def validate(repo:Path)->list[str]:
 errors=[]
 for rel in REQUIRED:
  if not (repo/rel).is_file(): errors.append(f'{rel}: missing')
 package=json.loads((repo/'frontend/package.json').read_text(encoding='utf-8'))
 if 'validate:phase4' not in package.get('scripts',{}): errors.append('package.json: validate:phase4 missing')
 store=(repo/'frontend/src/app/features/assistant-conversation/agent-conversation.store.ts').read_text(encoding='utf-8')
 for required in ('WorkplaceAgentApiService','sessionStorage','composeClarificationQuery','CLARIFICATION_REPLY_LIMIT','stopWaiting','retryLast'):
  if required not in store: errors.append(f'conversation store missing {required}')
 for forbidden in ('HttpClient','EventSource','WebSocket','setInterval(','setTimeout('):
  if forbidden in store: errors.append(f'conversation store contains forbidden direct transport or fake timing: {forbidden}')
 mapper=(repo/'frontend/src/app/features/assistant-conversation/agent-response.mapper.ts').read_text(encoding='utf-8')
 for forbidden in ('evidence_ids:', 'proposal.id', 'organization_id:'):
  if forbidden in mapper: errors.append(f'response mapper may expose internal identifier: {forbidden}')
 panel=(repo/'frontend/src/app/layout/assistant-panel/assistant-panel.component.html').read_text(encoding='utf-8')
 for required in ('app-assistant-composer','app-assistant-message','role="log"','Waiting for the backend response'):
  if required not in panel: errors.append(f'assistant panel missing {required}')
 for forbidden in ('chain-of-thought','proposal_internal','evidence_internal','organizationId','currentUser.userId()'):
  if forbidden in panel: errors.append(f'assistant panel exposes forbidden value: {forbidden}')
 shell=(repo/'frontend/src/app/layout/app-shell/app-shell.component.html').read_text(encoding='utf-8')
 if '[currentSection]="state.activeSection()"' not in shell: errors.append('app shell does not pass current workspace context to Ask AI')
 e2e=(repo/'frontend/e2e/assistant-conversation.spec.ts').read_text(encoding='utf-8')
 for scenario in ('real REST query','clarification context','governed proposal review'):
  if scenario not in e2e: errors.append(f'Playwright missing {scenario}')
 visible='\n'.join(path.read_text(encoding='utf-8') for path in (repo/'frontend/src/app').rglob('*.html'))
 for forbidden in ('Cloudflare','proposal_internal','evidence_internal','/agent/query'):
  if forbidden in visible: errors.append(f'visible templates contain forbidden implementation detail: {forbidden}')
 return errors

def main()->int:
 parser=argparse.ArgumentParser();parser.add_argument('--repo',default='.');args=parser.parse_args();errors=validate(Path(args.repo).resolve())
 if errors:
  print('Angular Phase 4 validation failed:');[print(f'- {e}') for e in errors];return 1
 print('Angular Phase 4 conversation is valid: REST responses, clarification context, safe proposals, and session boundaries pass.');return 0
if __name__=='__main__': raise SystemExit(main())
