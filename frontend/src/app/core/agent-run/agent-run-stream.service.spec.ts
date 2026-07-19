import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { APP_RUNTIME_CONFIG } from '../config/app-config.token';
import { AgentRunStreamService } from './agent-run-stream.service';
import { CurrentUserStore } from '../auth/current-user.store';

function fakeResponse(status: number, headers: Record<string, string> = {}, body: string | null = ''): Response {
  return new Response(body, { status, headers: { 'content-type': 'text/event-stream', ...headers } });
}

const terminalAccepted = { schema_version: 1, run_id: 'run_1', sequence: 1, type: 'run.accepted' as const, stage: 'request_acceptance', message: 'Request accepted', payload: null, terminal: true, occurred_at: '2026-07-19T00:00:00Z' };

function sseBody(event: Record<string, unknown>): string {
  return `id: ${String(event['sequence'])}\nevent: ${String(event['type'])}\ndata: ${JSON.stringify(event)}\n\n`;
}

describe('AgentRunStreamService', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    TestBed.configureTestingModule({
      providers: [
        AgentRunStreamService,
        { provide: APP_RUNTIME_CONFIG, useValue: { apiBaseUrl: '/api', defaultOrganizationId: 'org_1', mockUserId: 'usr_1', requestTimeoutMs: 30000, enableDebugViews: false, streamTransport: 'sse' } },
        { provide: CurrentUserStore, useValue: { userId: () => 'usr_1' } },
      ],
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('propagates fatal 401 response without reconnecting', async () => {
    const service = TestBed.inject(AgentRunStreamService);
    let callCount = 0;
    vi.stubGlobal('fetch', vi.fn(() => { callCount += 1; return Promise.resolve(fakeResponse(401)); }));
    const errors: unknown[] = [];
    const sub = service.watch('org_1', 'run_1', 0).subscribe({ error: (e) => errors.push(e) });
    await vi.advanceTimersByTimeAsync(200);
    sub.unsubscribe();
    expect(errors.length).toBe(1);
    expect(errors[0]).toBeInstanceOf(Error);
    expect(((errors[0] as Error) as unknown as { response: Response }).response.status).toBe(401);
    expect(callCount).toBe(1);
  });

  it('propagates fatal 403 response without reconnecting', async () => {
    const service = TestBed.inject(AgentRunStreamService);
    let callCount = 0;
    vi.stubGlobal('fetch', vi.fn(() => { callCount += 1; return Promise.resolve(fakeResponse(403)); }));
    const errors: unknown[] = [];
    const sub = service.watch('org_1', 'run_1', 0).subscribe({ error: (e) => errors.push(e) });
    await vi.advanceTimersByTimeAsync(200);
    sub.unsubscribe();
    expect(errors.length).toBe(1);
    expect(errors[0]).toBeInstanceOf(Error);
    expect(((errors[0] as Error) as unknown as { response: Response }).response.status).toBe(403);
    expect(callCount).toBe(1);
  });

  it('propagates fatal 404 response without reconnecting', async () => {
    const service = TestBed.inject(AgentRunStreamService);
    let callCount = 0;
    vi.stubGlobal('fetch', vi.fn(() => { callCount += 1; return Promise.resolve(fakeResponse(404)); }));
    const errors: unknown[] = [];
    const sub = service.watch('org_1', 'run_1', 0).subscribe({ error: (e) => errors.push(e) });
    await vi.advanceTimersByTimeAsync(200);
    sub.unsubscribe();
    expect(errors.length).toBe(1);
    expect(errors[0]).toBeInstanceOf(Error);
    expect(((errors[0] as Error) as unknown as { response: Response }).response.status).toBe(404);
    expect(callCount).toBe(1);
  });

  it('propagates invalid content type as protocol error', async () => {
    const service = TestBed.inject(AgentRunStreamService);
    let callCount = 0;
    vi.stubGlobal('fetch', vi.fn(() => { callCount += 1; return Promise.resolve(fakeResponse(200, { 'content-type': 'text/html' }, '<html>')); }));
    const errors: unknown[] = [];
    const sub = service.watch('org_1', 'run_1', 0).subscribe({ error: (e) => errors.push(e) });
    await vi.advanceTimersByTimeAsync(200);
    sub.unsubscribe();
    expect(errors.length).toBe(1);
    expect(errors[0]).toBeInstanceOf(Error);
    expect((errors[0] as Error).message).toContain('unexpected content type');
    expect(callCount).toBe(1);
  });

  it('propagates missing body as protocol error', async () => {
    const service = TestBed.inject(AgentRunStreamService);
    let callCount = 0;
    vi.stubGlobal('fetch', vi.fn(() => { callCount += 1; return Promise.resolve(fakeResponse(200, {}, null)); }));
    const errors: unknown[] = [];
    const sub = service.watch('org_1', 'run_1', 0).subscribe({ error: (e) => errors.push(e) });
    await vi.advanceTimersByTimeAsync(200);
    sub.unsubscribe();
    expect(errors.length).toBe(1);
    expect(errors[0]).toBeInstanceOf(Error);
    expect((errors[0] as Error).message).toContain('no response body');
    expect(callCount).toBe(1);
  });

  it('retries on 408 timeout response', async () => {
    const service = TestBed.inject(AgentRunStreamService);
    let callCount = 0;
    vi.stubGlobal('fetch', vi.fn(() => {
      callCount += 1;
      return Promise.resolve(callCount === 1 ? fakeResponse(408) : fakeResponse(200, {}, sseBody(terminalAccepted)));
    }));
    const events: unknown[] = [];
    const sub = service.watch('org_1', 'run_1', 0).subscribe({ next: (u) => { if (u.kind === 'event') events.push(u.event); } });
    await vi.advanceTimersByTimeAsync(3000);
    sub.unsubscribe();
    expect(callCount).toBeGreaterThanOrEqual(2);
    expect(events.length).toBeGreaterThanOrEqual(1);
  });

  it('retries on 500 server error', async () => {
    const service = TestBed.inject(AgentRunStreamService);
    let callCount = 0;
    vi.stubGlobal('fetch', vi.fn(() => {
      callCount += 1;
      return Promise.resolve(callCount === 1 ? fakeResponse(500) : fakeResponse(200, {}, sseBody(terminalAccepted)));
    }));
    const events: unknown[] = [];
    const sub = service.watch('org_1', 'run_1', 0).subscribe({ next: (u) => { if (u.kind === 'event') events.push(u.event); } });
    await vi.advanceTimersByTimeAsync(3000);
    sub.unsubscribe();
    expect(callCount).toBeGreaterThanOrEqual(2);
    expect(events.length).toBeGreaterThanOrEqual(1);
  });
});
