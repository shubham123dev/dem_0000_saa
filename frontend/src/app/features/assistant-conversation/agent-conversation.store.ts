import { DOCUMENT } from '@angular/common';
import { computed, DestroyRef, effect, inject, Injectable, signal } from '@angular/core';
import type { Subscription } from 'rxjs';
import { WorkplaceAgentApiService } from '../../core/api/workplace-agent-api.service';
import { APP_RUNTIME_CONFIG } from '../../core/config/app-config.token';
import { normalizeWorkplaceError } from '../../core/errors/error-normalizer';
import type { ConversationMessage, ConversationSnapshot, PendingClarification } from './agent-conversation.model';
import { conversationSnapshotSchema, emptyConversationMessage } from './agent-conversation.model';
import { mapAgentResponse } from './agent-response.mapper';

const STORAGE_KEY = 'dbmr-workplace-conversation-v1';
const SNAPSHOT_VERSION = 1;
const MAX_MESSAGES = 60;
const MAX_SNAPSHOT_BYTES = 220_000;
export const CLARIFICATION_REPLY_LIMIT = 1200;

interface SubmissionRecord {
  readonly displayText: string;
  readonly apiQuery: string;
  readonly rootOriginal: string;
  readonly collectedDetails: readonly string[];
  readonly contextNote: string | null;
}


function createOrganizationScope(value: string): string {
  let hash = 2166136261;
  for (const character of value) {
    hash ^= character.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return `scope-${(hash >>> 0).toString(16)}`;
}

function truncate(value: string, limit: number): string {
  const compact = value.trim();
  return compact.length <= limit ? compact : `${compact.slice(0, limit - 1)}…`;
}

export function composeClarificationQuery(context: PendingClarification, reply: string): string {
  const previousDetails = context.collectedDetails.length
    ? context.collectedDetails.map((detail, index) => `${index + 1}. ${detail}`).join('\n')
    : 'None yet.';
  const query = [
    'Original request:',
    truncate(context.originalRequest, 1300),
    '',
    'Previous clarification details:',
    truncate(previousDetails, 600),
    '',
    'Clarification requested by the workplace agent:',
    truncate(context.question, 500),
    '',
    'Additional details from the user:',
    truncate(reply, CLARIFICATION_REPLY_LIMIT),
    '',
    'Re-evaluate the original request using these details. Ask another clarification only when a required field is still missing.'
  ].join('\n');
  if (query.length > 4000) throw new Error('Clarification context exceeds the backend request limit.');
  return query;
}

@Injectable({ providedIn: 'root' })
export class AgentConversationStore {
  private readonly document = inject(DOCUMENT);
  private readonly destroyRef = inject(DestroyRef);
  private readonly config = inject(APP_RUNTIME_CONFIG);
  private readonly api = inject(WorkplaceAgentApiService);
  private readonly organizationId = this.config.defaultOrganizationId;
  private readonly organizationScope = this.organizationId ? createOrganizationScope(this.organizationId) : null;
  private readonly initialSnapshot = this.readSnapshot();
  private readonly messagesState = signal<ConversationMessage[]>(this.initialSnapshot?.messages ?? []);
  private readonly pendingState = signal(false);
  private readonly clarificationState = signal<PendingClarification | null>(this.initialSnapshot?.pendingClarification ?? null);
  private readonly retryMessageIdState = signal<string | null>(null);
  private activeRequest: Subscription | null = null;
  private lastSubmission: SubmissionRecord | null = null;

  readonly messages = this.messagesState.asReadonly();
  readonly pending = this.pendingState.asReadonly();
  readonly pendingClarification = this.clarificationState.asReadonly();
  readonly retryMessageId = this.retryMessageIdState.asReadonly();
  readonly hasMessages = computed(() => this.messages().length > 0);
  readonly inputLimit = computed(() => this.pendingClarification() ? CLARIFICATION_REPLY_LIMIT : 4000);
  readonly configured = computed(() => Boolean(this.organizationId));
  readonly canSubmit = computed(() => this.configured() && !this.pending());

  constructor() {
    effect(() => this.persistSnapshot(this.messages(), this.pendingClarification()));
    this.destroyRef.onDestroy(() => this.activeRequest?.unsubscribe());
  }

  submit(text: string): void {
    const normalized = text.trim();
    if (!normalized || !this.canSubmit() || normalized.length > this.inputLimit()) return;
    const clarification = this.pendingClarification();
    const submission: SubmissionRecord = clarification
      ? {
          displayText: normalized,
          apiQuery: composeClarificationQuery(clarification, normalized),
          rootOriginal: clarification.originalRequest,
          collectedDetails: [...clarification.collectedDetails, normalized],
          contextNote: 'Sent together with the original request and earlier clarification details.'
        }
      : {
          displayText: normalized,
          apiQuery: normalized,
          rootOriginal: normalized,
          collectedDetails: [],
          contextNote: null
        };
    this.send(submission);
  }

  retryLast(): void {
    if (!this.lastSubmission || this.pending()) return;
    this.send({
      ...this.lastSubmission,
      contextNote: 'Retried manually. Check Pending approvals if the earlier request may have completed.'
    });
  }

  stopWaiting(): void {
    if (!this.pending()) return;
    this.activeRequest?.unsubscribe();
    this.activeRequest = null;
    this.pendingState.set(false);
    this.retryMessageIdState.set(null);
    this.append({
      ...emptyConversationMessage(
        'notice',
        'Stopped waiting for this response. The backend may still have completed the read or prepared a proposal, so check Pending approvals before repeating the request.',
        this.createId(),
        this.now()
      ),
      tone: 'warning',
      title: 'Browser request stopped'
    });
  }

  dismissClarification(): void {
    this.clarificationState.set(null);
  }

  clearConversation(): void {
    this.activeRequest?.unsubscribe();
    this.activeRequest = null;
    this.lastSubmission = null;
    this.pendingState.set(false);
    this.retryMessageIdState.set(null);
    this.clarificationState.set(null);
    this.messagesState.set([]);
    this.removeSnapshot();
  }

  private send(submission: SubmissionRecord): void {
    if (!this.organizationId) return;
    this.activeRequest?.unsubscribe();
    this.lastSubmission = submission;
    this.retryMessageIdState.set(null);
    this.append({
      ...emptyConversationMessage('user', submission.displayText, this.createId(), this.now()),
      contextNote: submission.contextNote
    });
    this.pendingState.set(true);

    this.activeRequest = this.api.query(this.organizationId, submission.apiQuery).subscribe({
      next: (response) => {
        this.append(mapAgentResponse(response, this.createId(), this.now()));
        if (response.mode === 'clarification_required') {
          this.clarificationState.set({
            originalRequest: submission.rootOriginal,
            collectedDetails: [...submission.collectedDetails].slice(-8),
            question: truncate(response.answer, 4000),
            missingFields: response.missing_fields.slice(0, 20).map((field) => truncate(field, 160))
          });
        } else {
          this.clarificationState.set(null);
        }
      },
      error: (error: unknown) => {
        const normalized = normalizeWorkplaceError(error);
        const messageId = this.createId();
        this.append({
          ...emptyConversationMessage('error', normalized.message, messageId, this.now()),
          tone: 'danger',
          title: normalized.title,
          retryable: normalized.retryable
        });
        this.retryMessageIdState.set(normalized.retryable ? messageId : null);
        this.pendingState.set(false);
        this.activeRequest = null;
      },
      complete: () => {
        this.pendingState.set(false);
        this.activeRequest = null;
      }
    });
  }

  private append(message: ConversationMessage): void {
    this.messagesState.update((messages) => [...messages, message].slice(-MAX_MESSAGES));
  }

  private now(): string {
    return new Date().toISOString();
  }

  private createId(): string {
    return globalThis.crypto?.randomUUID?.() ?? `message-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }

  private readSnapshot(): ConversationSnapshot | null {
    if (!this.organizationScope) return null;
    try {
      const raw = this.document.defaultView?.sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      const parsed: unknown = JSON.parse(raw);
      const snapshot = conversationSnapshotSchema.parse(parsed);
      return snapshot.organizationScope === this.organizationScope ? snapshot : null;
    } catch {
      this.removeSnapshot();
      return null;
    }
  }

  private persistSnapshot(messages: readonly ConversationMessage[], pendingClarification: PendingClarification | null): void {
    if (!this.organizationScope) return;
    const snapshot: ConversationSnapshot = {
      version: SNAPSHOT_VERSION,
      organizationScope: this.organizationScope,
      messages: [...messages].slice(-MAX_MESSAGES),
      pendingClarification
    };
    try {
      let encoded = JSON.stringify(snapshot);
      if (encoded.length > MAX_SNAPSHOT_BYTES) {
        encoded = JSON.stringify({ ...snapshot, messages: snapshot.messages.slice(-20) });
      }
      this.document.defaultView?.sessionStorage.setItem(STORAGE_KEY, encoded);
    } catch {
      // Session storage is an optional convenience and never blocks the agent.
    }
  }

  private removeSnapshot(): void {
    try {
      this.document.defaultView?.sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      // Storage may be disabled.
    }
  }
}
