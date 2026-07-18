import { TestBed } from '@angular/core/testing';
import { of, Subject } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AgentRunApiService } from '../../core/agent-run/agent-run-api.service';
import type { AgentRunStreamUpdate } from '../../core/agent-run/agent-run.models';
import { AgentRunStreamService } from '../../core/agent-run/agent-run-stream.service';
import { WorkplaceAgentApiService } from '../../core/api/workplace-agent-api.service';
import { APP_RUNTIME_CONFIG } from '../../core/config/app-config.token';
import { AgentConversationStore } from './agent-conversation.store';

const created = {
  conversation_id: 'conversation_1',
  run: {
    id: 'run_1', conversation_id: 'conversation_1', status: 'queued',
    current_stage: 'request_acceptance', final_mode: null, error_code: null,
    cancellation_requested_at: null, attempt_count: 0, terminal: false,
    created_at: '2026-07-19T00:00:00Z', started_at: null, completed_at: null
  },
  user_message: {
    id: 'message_1', sequence: 1, role: 'user', content: 'List users',
    mode: null, answer_source: null, safe_metadata: null,
    created_at: '2026-07-19T00:00:00Z'
  },
  events_url: '/events', created: true
} as const;

describe('AgentConversationStore durable runs', () => {
  let updates: Subject<AgentRunStreamUpdate>;
  let cancel: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    sessionStorage.clear();
    updates = new Subject();
    cancel = vi.fn().mockReturnValue(of({ ...created.run, status: 'cancel_requested' }));
    TestBed.configureTestingModule({ providers: [
      { provide: APP_RUNTIME_CONFIG, useValue: { apiBaseUrl: '/api', defaultOrganizationId: 'org_1', mockUserId: 'usr_1', requestTimeoutMs: 30000, enableDebugViews: false, streamTransport: 'sse' } },
      { provide: WorkplaceAgentApiService, useValue: { query: vi.fn() } },
      { provide: AgentRunApiService, useValue: {
        create: vi.fn().mockReturnValue(of(created)),
        conversation: vi.fn().mockReturnValue(of({ conversation_id: 'conversation_1', messages: [created.user_message], active_run: created.run })),
        cancel
      } },
      { provide: AgentRunStreamService, useValue: { watch: vi.fn().mockReturnValue(updates) } }
    ] });
  });

  it('submits once and renders the terminal SSE message', () => {
    const store = TestBed.inject(AgentConversationStore);
    store.submit('List users');
    updates.next({ kind: 'event', event: { schema_version: 1, run_id: 'run_1', sequence: 1, type: 'run.accepted', stage: 'request_acceptance', message: 'Request accepted', payload: null, terminal: false, occurred_at: '2026-07-19T00:00:00Z' } });
    updates.next({ kind: 'event', event: { schema_version: 1, run_id: 'run_1', sequence: 2, type: 'answer.completed', stage: 'completion', message: 'Answer ready', payload: { message: { id: 'message_2', sequence: 2, role: 'assistant', content: 'Two users.', mode: 'read', answer_source: 'deterministic', safe_metadata: { source_count: 1, missing_fields: [] }, created_at: '2026-07-19T00:00:01Z' } }, terminal: true, occurred_at: '2026-07-19T00:00:01Z' } });
    expect(store.messages().map((message) => message.text)).toEqual(['List users', 'Two users.']);
    expect(store.pending()).toBe(false);
    TestBed.flushEffects();
    const persisted = sessionStorage.getItem('dbmr-workplace-conversation-v2') ?? '';
    expect(persisted).toContain('conversation_1');
    expect(persisted).not.toContain('Two users.');
  });

  it('stops watching without clearing or resubmitting the active run', () => {
    const store = TestBed.inject(AgentConversationStore);
    store.submit('List users');
    store.stopWaiting();
    expect(store.canResume()).toBe(true);
    expect(store.messages().at(-1)?.text).toContain('continues safely in the backend');
  });

  it('requests cooperative cancellation and keeps watching for the terminal event', () => {
    const store = TestBed.inject(AgentConversationStore);
    store.submit('List users');
    store.cancelActiveRun();
    expect(cancel).toHaveBeenCalledWith('org_1', 'run_1');
    expect(store.cancellationRequested()).toBe(true);
  });

  it('starts a new server conversation when clarification is abandoned', () => {
    const store = TestBed.inject(AgentConversationStore);
    store.submit('List users');
    store.dismissClarification();
    expect(store.messages()).toEqual([]);
    expect(sessionStorage.getItem('dbmr-workplace-conversation-v2')).toBeNull();
  });
});
