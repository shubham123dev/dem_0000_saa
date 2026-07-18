import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { CurrentUserStore } from '../auth/current-user.store';
import { APP_RUNTIME_CONFIG } from '../config/app-config.token';
import type { AgentRunEvent, AgentRunStreamUpdate } from './agent-run.models';
import { agentRunEventSchema } from './agent-run.schemas';
import { SseFrameParser, type SseFrame } from './sse-frame-parser';

function encode(value: string): string { return encodeURIComponent(value); }

class AgentRunStreamProtocolError extends Error {}

@Injectable({ providedIn: 'root' })
export class AgentRunStreamService {
  private readonly config = inject(APP_RUNTIME_CONFIG);
  private readonly user = inject(CurrentUserStore);

  watch(
    organizationId: string,
    runId: string,
    afterSequence: number,
    externalSignal?: AbortSignal
  ): Observable<AgentRunStreamUpdate> {
    return new Observable((subscriber) => {
      const controller = new AbortController();
      const abort = (): void => controller.abort();
      externalSignal?.addEventListener('abort', abort, { once: true });
      void this.consume(
        organizationId,
        runId,
        afterSequence,
        controller.signal,
        (update) => subscriber.next(update)
      ).then(
        () => subscriber.complete(),
        (error: unknown) => subscriber.error(error)
      );
      return () => {
        externalSignal?.removeEventListener('abort', abort);
        controller.abort();
      };
    });
  }

  private async consume(
    organizationId: string,
    runId: string,
    initialSequence: number,
    signal: AbortSignal,
    emit: (update: AgentRunStreamUpdate) => void
  ): Promise<void> {
    let sequence = initialSequence;
    let attempt = 0;
    while (!signal.aborted) {
      emit({ kind: 'state', state: attempt === 0 ? 'connecting' : 'reconnecting' });
      try {
        const terminalSequence = await this.openOnce(
          organizationId,
          runId,
          sequence,
          signal,
          emit,
          (next) => {
            sequence = Math.max(sequence, next);
            attempt = 0;
          }
        );
        if (terminalSequence !== null) {
          emit({ kind: 'state', state: 'closed' });
          return;
        }
        attempt += 1;
      } catch (error: unknown) {
        if (signal.aborted) return;
        attempt += 1;
        if (error instanceof AgentRunStreamProtocolError || this.isFatalResponse(error)) {
          throw error;
        }
      }
      await this.delay(Math.min(5000, 400 * 2 ** Math.min(attempt, 4)), signal);
    }
  }

  private async openOnce(
    organizationId: string,
    runId: string,
    afterSequence: number,
    signal: AbortSignal,
    emit: (update: AgentRunStreamUpdate) => void,
    advance: (sequence: number) => void
  ): Promise<number | null> {
    const userId = this.user.userId();
    if (!userId) throw new AgentRunStreamProtocolError('No authenticated sandbox user is configured.');
    const path = `/workplace/organizations/${encode(organizationId)}/agent/runs/${encode(runId)}/events`;
    const requestId = globalThis.crypto?.randomUUID?.() ?? `stream-${Date.now()}`;
    const response = await fetch(`${this.config.apiBaseUrl}${path}?after_sequence=${afterSequence}`, {
      method: 'GET',
      cache: 'no-store',
      credentials: 'same-origin',
      headers: {
        Accept: 'text/event-stream',
        'X-Mock-User-Id': userId,
        'X-Request-Id': requestId,
        'Last-Event-ID': String(afterSequence)
      },
      signal
    });
    if (!response.ok || !response.body) throw new Error(`SSE request failed with status ${response.status}`);
    const contentType = response.headers.get('content-type') ?? '';
    if (!contentType.toLowerCase().startsWith('text/event-stream')) {
      throw new AgentRunStreamProtocolError('The run stream returned an unexpected content type.');
    }
    emit({ kind: 'state', state: 'open' });
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const parser = new SseFrameParser();
    try {
      while (!signal.aborted) {
        const result = await reader.read();
        const chunk = decoder.decode(result.value ?? new Uint8Array(), { stream: !result.done });
        for (const frame of parser.push(chunk)) {
          const event = this.parseEvent(frame);
          if (event.sequence <= afterSequence) continue;
          afterSequence = event.sequence;
          advance(afterSequence);
          emit({ kind: 'event', event });
          if (event.terminal) return event.sequence;
        }
        if (result.done) {
          for (const frame of parser.finish()) {
            const event = this.parseEvent(frame);
            if (event.sequence <= afterSequence) continue;
            afterSequence = event.sequence;
            advance(afterSequence);
            emit({ kind: 'event', event });
            if (event.terminal) return event.sequence;
          }
          return null;
        }
      }
      return null;
    } finally {
      reader.releaseLock();
    }
  }

  private parseEvent(frame: SseFrame): AgentRunEvent {
    let payload: unknown;
    try {
      payload = JSON.parse(frame.data) as unknown;
    } catch (error: unknown) {
      void error;
      throw new AgentRunStreamProtocolError('The run stream returned invalid JSON.');
    }
    const parsed = agentRunEventSchema.safeParse(payload);
    if (!parsed.success) {
      throw new AgentRunStreamProtocolError(`The run stream returned an invalid event: ${parsed.error.issues[0]?.message ?? 'schema mismatch'}.`);
    }
    if (frame.id !== null && frame.id !== String(parsed.data.sequence)) {
      throw new AgentRunStreamProtocolError('The run stream event ID does not match its sequence.');
    }
    if (frame.event !== 'message' && frame.event !== parsed.data.type) {
      throw new AgentRunStreamProtocolError('The run stream event name does not match its payload.');
    }
    return parsed.data;
  }

  private isFatalResponse(error: unknown): boolean {
    if (!(error instanceof Response)) return false;
    return error.status >= 400 && error.status < 500 && ![408, 425, 429].includes(error.status);
  }

  private delay(milliseconds: number, signal: AbortSignal): Promise<void> {
    if (signal.aborted) return Promise.resolve();
    return new Promise((resolve) => {
      const finish = (): void => {
        signal.removeEventListener('abort', finish);
        globalThis.clearTimeout(timeout);
        resolve();
      };
      const timeout = globalThis.setTimeout(finish, milliseconds);
      signal.addEventListener('abort', finish, { once: true });
    });
  }
}
