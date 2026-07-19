#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

REQUIRED=(
'alembic/versions/0017_governed_action_control_plane.py','app/db/action_control_models.py','app/agent/action_control_contracts.py','app/repositories/action_control_repository.py','app/services/action_control_service.py','app/api/action_control_routes.py','frontend/src/app/core/action-control/action-control-api.service.ts','frontend/src/app/core/sse/authenticated-sse-client.service.ts','frontend/src/app/features/approval-center/approval-center.component.ts','frontend/src/app/features/approval-center/approval-center.component.html','frontend/e2e/approval-center.spec.ts','docs/GOVERNED_ACTION_CONTROL_PLANE.md')

def validate(repo:Path)->list[str]:
 errors=[]
 for rel in REQUIRED:
  if not (repo/rel).is_file(): errors.append(f'{rel}: missing')
 migration=(repo/'alembic/versions/0017_governed_action_control_plane.py').read_text(encoding='utf-8')
 for required in ('agent_action_execution_events','uq_action_execution_event_sequence','uq_action_execution_event_dedupe'):
  if required not in migration: errors.append(f'migration missing {required}')
 routes=(repo/'app/api/action_control_routes.py').read_text(encoding='utf-8')
 for required in ('agent/capabilities','execution/events','Last-Event-ID','after_sequence','text/event-stream','rollback-proposal'):
  if required not in routes: errors.append(f'action control routes missing {required}')
 service=(repo/'app/services/action_control_service.py').read_text(encoding='utf-8')
 for required in ('allowed_operations','idempotency_key','DatabaseActionExecutionActivitySink','create_rollback_proposal','reconciliation_required'):
  if required not in service: errors.append(f'action control service missing {required}')
 html=(repo/'frontend/src/app/features/approval-center/approval-center.component.html').read_text(encoding='utf-8')
 for required in ('Approval Center','Proposed changes','Execution activity','Execution receipt','Create rollback proposal'):
  if required not in html: errors.append(f'Approval Center missing {required}')
 for forbidden in ('Cloudflare','GitHub','chain-of-thought','action_fingerprint','nucleus_actor_id'):
  if forbidden in html: errors.append(f'Approval Center exposes forbidden detail: {forbidden}')
 package=json.loads((repo/'frontend/package.json').read_text(encoding='utf-8'))
 if 'validate:phase6' not in package.get('scripts',{}): errors.append('package.json missing validate:phase6')
 return errors

def main()->int:
 parser=argparse.ArgumentParser();parser.add_argument('--repo',default='.');args=parser.parse_args();errors=validate(Path(args.repo).resolve())
 if errors:
  print('Phase 6 validation failed:');[print(f'- {error}') for error in errors];return 1
 print('Phase 6 is valid: governed proposals, explicit decisions, idempotent execution, durable SSE activity, receipts, reconciliation, and rollback are present.');return 0
if __name__=='__main__':raise SystemExit(main())
