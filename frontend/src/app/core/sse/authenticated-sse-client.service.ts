import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import type { z } from 'zod';
import { CurrentUserStore } from '../auth/current-user.store';
import { APP_RUNTIME_CONFIG } from '../config/app-config.token';
import { SseFrameParser } from '../agent-run/sse-frame-parser';

export type SseConnectionState = 'connecting' | 'open' | 'reconnecting' | 'closed';
export type AuthenticatedSseUpdate<T> =
  | { readonly kind: 'state'; readonly state: SseConnectionState }
  | { readonly kind: 'event'; readonly event: T };

export class AuthenticatedSseResponseError extends Error {
  constructor(readonly response: Response) {
    super(`SSE request failed with status ${response.status}`);
    this.name = 'AuthenticatedSseResponseError';
  }
}

export class AuthenticatedSseProtocolError extends Error {
  constructor(message: string) { super(message); this.name = 'AuthenticatedSseProtocolError'; }
}

@Injectable({ providedIn: 'root' })
export class AuthenticatedSseClient {
  private readonly config = inject(APP_RUNTIME_CONFIG);
  private readonly user = inject(CurrentUserStore);

  watch<T>(path: string, schema: z.ZodType<T>, afterSequence = 0, externalSignal?: AbortSignal): Observable<AuthenticatedSseUpdate<T>> {
    return new Observable((subscriber) => {
      const controller = new AbortController();
      const abort = (): void => controller.abort();
      externalSignal?.addEventListener('abort', abort, { once: true });
      void this.consume(path, schema, afterSequence, controller.signal, (update) => subscriber.next(update)).then(
        () => subscriber.complete(), (error: unknown) => subscriber.error(error)
      );
      return () => {
        externalSignal?.removeEventListener('abort', abort);
        controller.abort();
      };
    });
  }

  private async consume<T>(path: string, schema: z.ZodType<T>, initialSequence: number, signal: AbortSignal, emit: (update: AuthenticatedSseUpdate<T>) => void): Promise<void> {
    let sequence = initialSequence;
    let attempt = 0;
    while (!signal.aborted) {
      emit({ kind: 'state', state: attempt === 0 ? 'connecting' : 'reconnecting' });
      try {
        const terminal = await this.openOnce(path, schema, sequence, signal, emit, (next) => { sequence = Math.max(sequence, next); });
        if (terminal) { emit({ kind: 'state', state: 'closed' }); return; }
        attempt += 1;
      } catch (error: unknown) {
        if (signal.aborted) return;
        if (this.isFatal(error)) throw error;
        attempt += 1;
      }
      await this.delay(Math.min(5000, 400 * 2 ** Math.min(attempt, 4)), signal);
    }
  }

  private async openOnce<T>(path: string, schema: z.ZodType<T>, afterSequence: number, signal: AbortSignal, emit: (update: AuthenticatedSseUpdate<T>) => void, advance: (sequence: number) => void): Promise<boolean> {
    const userId = this.user.userId();
    if (!userId) throw new AuthenticatedSseProtocolError('No authenticated sandbox user is configured.');
    const separator = path.includes('?') ? '&' : '?';
    const response = await fetch(`${this.config.apiBaseUrl}${path}${separator}after_sequence=${afterSequence}`, {
      method: 'GET', cache: 'no-store', credentials: 'same-origin', signal,
      headers: { Accept: 'text/event-stream', 'X-Mock-User-Id': userId, 'Last-Event-ID': String(afterSequence) }
    });
    if (!response.ok) throw new AuthenticatedSseResponseError(response);
    const contentType = response.headers.get('content-type')?.toLowerCase() ?? '';
    if (!contentType.includes('text/event-stream')) throw new AuthenticatedSseProtocolError('The server did not return an SSE stream.');
    if (!response.body) throw new AuthenticatedSseProtocolError('The run stream returned no response body.');
    emit({ kind: 'state', state: 'open' });
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const parser = new SseFrameParser();
    try {
      while (!signal.aborted) {
        const result = await reader.read();
        const frames = parser.push(decoder.decode(result.value ?? new Uint8Array(), { stream: !result.done }));
        for (const frame of frames) {
          let value: unknown;
          try { value = JSON.parse(frame.data) as unknown; }
          catch { throw new AuthenticatedSseProtocolError('The stream returned invalid JSON.'); }
          const parsed = schema.safeParse(value);
          if (!parsed.success) throw new AuthenticatedSseProtocolError('The stream returned an invalid event.');
          const event = parsed.data as T & { sequence: number; terminal: boolean; type?: string };
          if (frame.id !== null && Number(frame.id) !== event.sequence) throw new AuthenticatedSseProtocolError('The stream event ID does not match its sequence.');
          if (frame.event !== 'message' && event.type && frame.event !== event.type) throw new AuthenticatedSseProtocolError('The stream event name does not match its payload.');
          if (event.sequence <= afterSequence) continue;
          afterSequence = event.sequence; advance(afterSequence); emit({ kind: 'event', event: parsed.data });
          if (event.terminal) return true;
        }
        if (result.done) {
          for (const frame of parser.finish()) {
            let value: unknown;
            try { value = JSON.parse(frame.data) as unknown; }
            catch { throw new AuthenticatedSseProtocolError('The stream returned invalid JSON.'); }
            const parsed = schema.safeParse(value);
            if (!parsed.success) throw new AuthenticatedSseProtocolError('The stream returned an invalid event.');
            const event = parsed.data as T & { sequence: number; terminal: boolean; type?: string };
            if (event.sequence > afterSequence) {
              advance(event.sequence); emit({ kind: 'event', event: parsed.data });
              if (event.terminal) return true;
            }
          }
          return false;
        }
      }
      return false;
    } finally { reader.releaseLock(); }
  }

  private isFatal(error: unknown): boolean {
    if (error instanceof AuthenticatedSseProtocolError) return true;
    if (!(error instanceof AuthenticatedSseResponseError)) return false;
    const status = error.response.status;
    return status >= 400 && status < 500 && ![408, 425, 429].includes(status);
  }

  private delay(milliseconds: number, signal: AbortSignal): Promise<void> {
    return new Promise((resolve, reject) => {
      const timeout = globalThis.setTimeout(resolve, milliseconds);
      signal.addEventListener('abort', () => {
        globalThis.clearTimeout(timeout);
        reject(new DOMException('Aborted', 'AbortError'));
      }, { once: true });
    });
  }
}
