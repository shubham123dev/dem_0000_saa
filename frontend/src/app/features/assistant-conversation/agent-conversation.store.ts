import { DOCUMENT } from '@angular/common';
import { computed, DestroyRef, effect, inject, Injectable, signal } from '@angular/core';
import { map, switchMap, type Subscription } from 'rxjs';
import { AgentRunApiService } from '../../core/agent-run/agent-run-api.service';
import type { AgentRunEvent, AgentRunMessage, AgentRunStreamUpdate } from '../../core/agent-run/agent-run.models';
import { agentRunMessageSchema } from '../../core/agent-run/agent-run.schemas';
import { AgentRunStreamService } from '../../core/agent-run/agent-run-stream.service';
import { WorkplaceAgentApiService } from '../../core/api/workplace-agent-api.service';
import { CurrentUserStore } from '../../core/auth/current-user.store';
import { OrganizationRouteService } from '../../core/routing/organization-route.service';
import { APP_RUNTIME_CONFIG } from '../../core/config/app-config.token';
import { normalizeWorkplaceError } from '../../core/errors/error-normalizer';
import { WorkplaceApiError } from '../../core/errors/workplace-api.error';
import type { AgentActivityItem, AgentConversationRecovery, AgentRunConnectionState } from './agent-activity.model';
import type { ConversationMessage, PendingClarification } from './agent-conversation.model';
import { emptyConversationMessage } from './agent-conversation.model';
import { mapAgentResponse, mapAgentRunMessage } from './agent-response.mapper';

const STORAGE_KEY = 'dbmr-workplace-conversation-v2';
const MAX_MESSAGES = 100;
export const CLARIFICATION_REPLY_LIMIT = 1200;

interface SubmissionRecord {
  readonly displayText: string;
  readonly apiQuery: string;
  readonly clientRequestId: string;
}

function organizationScope(value: string): string {
  let hash = 2166136261;
  for (const character of value) { hash ^= character.charCodeAt(0); hash = Math.imul(hash, 16777619); }
  return `scope-${(hash >>> 0).toString(16)}`;
}

export function composeClarificationQuery(context: PendingClarification, reply: string): string {
  const details = context.collectedDetails.length ? context.collectedDetails.join('\n') : 'None yet.';
  return ['Original request:', context.originalRequest.slice(0,1300), '', 'Previous clarification details:', details.slice(0,600), '', 'Clarification requested by the workplace agent:', context.question.slice(0,500), '', 'Additional details from the user:', reply.slice(0,CLARIFICATION_REPLY_LIMIT)].join('\n').slice(0,4000);
}

@Injectable({ providedIn: 'root' })
export class AgentConversationStore {
  private readonly document = inject(DOCUMENT);
  private readonly destroyRef = inject(DestroyRef);
  private readonly config = inject(APP_RUNTIME_CONFIG);
  private readonly currentUser = inject(CurrentUserStore);
  private readonly orgRoute = inject(OrganizationRouteService);
  private readonly restApi = inject(WorkplaceAgentApiService);
  private readonly runApi = inject(AgentRunApiService);
  private readonly stream = inject(AgentRunStreamService);

  /** Organization context now comes from the URL route parameter. */
  get organizationId(): string | null {
    return this.orgRoute.organizationId();
  }

  get scope(): string | null {
    return this.organizationId ? organizationScope(this.organizationId) : null;
  }

  private readonly messagesState = signal<ConversationMessage[]>([]);
  private readonly activitiesState = signal<AgentActivityItem[]>([]);
  private readonly pendingState = signal(false);
  private readonly clarificationState = signal<PendingClarification | null>(null);
  private readonly retryMessageIdState = signal<string | null>(null);
  private readonly connectionState = signal<AgentRunConnectionState>('closed');
  private readonly conversationIdState = signal<string | null>(null);
  private readonly activeRunIdState = signal<string | null>(null);
  private readonly lastEventSequenceState = signal(0);
  private readonly cancellationRequestedState = signal(false);
  private readonly watchingStoppedState = signal(false);
  private requestSubscription: Subscription | null = null;
  private streamSubscription: Subscription | null = null;
  private streamAbort: AbortController | null = null;
  private lastSubmission: SubmissionRecord | null = null;

  readonly messages = this.messagesState.asReadonly();
  readonly activities = this.activitiesState.asReadonly();
  readonly pending = this.pendingState.asReadonly();
  readonly pendingClarification = this.clarificationState.asReadonly();
  readonly retryMessageId = this.retryMessageIdState.asReadonly();
  readonly connection = this.connectionState.asReadonly();
  readonly cancellationRequested = this.cancellationRequestedState.asReadonly();
  readonly streamingEnabled = computed(() => this.config.streamTransport === 'sse');
  readonly hasMessages = computed(() => this.messages().length > 0);
  readonly inputLimit = computed(() => this.pendingClarification() ? CLARIFICATION_REPLY_LIMIT : 4000);
  readonly configured = computed(() => Boolean(this.organizationId));
  readonly canSubmit = computed(() => this.configured() && !this.pending() && !this.activeRunIdState());
  readonly canCancel = computed(() => this.streamingEnabled() && Boolean(this.activeRunIdState()) && !this.cancellationRequested());
  readonly canResume = computed(() => this.streamingEnabled() && Boolean(this.activeRunIdState()) && this.watchingStoppedState());

  constructor() {
    effect(() => this.persistRecovery());
    this.destroyRef.onDestroy(() => this.stopAll());
    effect(() => {
      const orgId = this.orgRoute.organizationId();
      const authenticated = this.currentUser.isAuthenticated();
      if (orgId && authenticated && this.streamingEnabled() && !this.conversationIdState()) {
        const recovery = this.readRecovery();
        if (recovery?.conversationId) {
          this.conversationIdState.set(recovery.conversationId);
          this.activeRunIdState.set(recovery.activeRunId);
          this.lastEventSequenceState.set(recovery.lastEventSequence);
          queueMicrotask(() => this.recover());
        }
      }
    });
  }

  submit(text: string): void {
    const normalized = text.trim();
    if (!normalized || !this.canSubmit() || normalized.length > this.inputLimit()) return;
    if (this.streamingEnabled()) this.submitRun(normalized);
    else this.submitRest(normalized);
  }

  retryLast(): void {
    if (!this.lastSubmission || this.pending()) return;
    if (this.streamingEnabled()) this.submitRun(this.lastSubmission.displayText, this.lastSubmission.clientRequestId);
    else this.submitRest(this.lastSubmission.displayText);
  }

  stopWaiting(): void {
    if (!this.pending()) return;
    if (this.streamingEnabled() && this.activeRunIdState()) {
      this.streamAbort?.abort();
      this.streamSubscription?.unsubscribe();
      this.streamSubscription = null;
      this.pendingState.set(false);
      this.connectionState.set('closed');
      this.watchingStoppedState.set(true);
      this.appendNotice('Stopped watching this run. It continues safely in the backend and can be resumed without resubmitting.', 'Run still active');
      return;
    }
    this.requestSubscription?.unsubscribe();
    this.requestSubscription = null;
    this.pendingState.set(false);
    this.appendNotice('Stopped waiting for this response. The backend may still have completed the request.', 'Browser request stopped');
  }

  resumeWatching(): void {
    const runId = this.activeRunIdState();
    if (!runId || !this.organizationId) return;
    this.watchingStoppedState.set(false);
    this.pendingState.set(true);
    this.connect(runId);
  }

  cancelActiveRun(): void {
    const runId = this.activeRunIdState();
    if (!runId || !this.organizationId || !this.canCancel()) return;
    this.cancellationRequestedState.set(true);
    this.runApi.cancel(this.organizationId, runId).subscribe({
      next: () => { if (this.watchingStoppedState()) this.resumeWatching(); },
      error: (error: unknown) => {
        this.cancellationRequestedState.set(false);
        this.appendError(error);
      }
    });
  }

  dismissClarification(): void { this.clearConversation(); }

  clearConversation(): void {
    this.stopAll();
    this.lastSubmission = null;
    this.messagesState.set([]);
    this.activitiesState.set([]);
    this.pendingState.set(false);
    this.clarificationState.set(null);
    this.retryMessageIdState.set(null);
    this.connectionState.set('closed');
    this.conversationIdState.set(null);
    this.activeRunIdState.set(null);
    this.lastEventSequenceState.set(0);
    this.cancellationRequestedState.set(false);
    this.watchingStoppedState.set(false);
    this.removeRecovery();
  }

  private submitRun(displayText: string, existingRequestId?: string): void {
    if (!this.organizationId) return;
    const clientRequestId = existingRequestId ?? (globalThis.crypto?.randomUUID?.() ?? `request-${Date.now()}`);
    this.lastSubmission = { displayText, apiQuery: displayText, clientRequestId };
    this.retryMessageIdState.set(null);
    this.pendingState.set(true);
    this.watchingStoppedState.set(false);
    this.activitiesState.set([]);
    this.requestSubscription?.unsubscribe();
    this.requestSubscription = this.runApi.create(this.organizationId, {
      query: displayText,
      client_request_id: clientRequestId,
      conversation_id: this.conversationIdState()
    }).pipe(
      switchMap((created) => this.runApi.conversation(this.organizationId!, created.conversation_id).pipe(map((conversation) => ({ created, conversation }))))
    ).subscribe({
      next: ({ created, conversation }) => {
        this.conversationIdState.set(created.conversation_id);
        this.activeRunIdState.set(created.run.id);
        this.lastEventSequenceState.set(0);
        this.messagesState.set(conversation.messages.map(mapAgentRunMessage).slice(-MAX_MESSAGES));
        this.pendingState.set(true);
        this.connect(created.run.id);
      },
      error: (error: unknown) => {
        this.pendingState.set(false);
        this.appendError(error, true);
      }
    });
  }

  private connect(runId: string): void {
    if (!this.organizationId) return;
    this.streamAbort?.abort();
    this.streamSubscription?.unsubscribe();
    this.streamAbort = new AbortController();
    this.streamSubscription = this.stream.watch(
      this.organizationId, runId, this.lastEventSequenceState(), this.streamAbort.signal
    ).subscribe({
      next: (update) => this.handleStreamUpdate(update),
      error: (error: unknown) => {
        this.pendingState.set(false);
        this.connectionState.set('closed');
        this.watchingStoppedState.set(true);
        this.appendError(error);
      },
      complete: () => {
        if (!this.activeRunIdState()) this.pendingState.set(false);
      }
    });
  }

  private handleStreamUpdate(update: AgentRunStreamUpdate): void {
    if (update.kind === 'state') {
      this.connectionState.set(update.state);
      return;
    }
    const event = update.event;
    if (event.sequence <= this.lastEventSequenceState()) return;
    this.lastEventSequenceState.set(event.sequence);
    if (event.type === 'run.cancel_requested') this.cancellationRequestedState.set(true);
    if (!event.terminal) this.recordActivity(event);
    if (event.terminal) this.finishFromEvent(event);
  }

  private recordActivity(event: AgentRunEvent): void {
    this.activitiesState.update((items) => {
      const completed = items.map((item) => ({ ...item, state: 'completed' as const }));
      return [...completed, { sequence:event.sequence, stage:event.stage, message:event.message, occurredAt:event.occurred_at, state:'active' as const }].slice(-12);
    });
  }

  private finishFromEvent(event: AgentRunEvent): void {
    this.activitiesState.update((items) => items.map((item) => ({ ...item, state:'completed' as const })));
    const candidate = event.payload?.['message'];
    const parsed = agentRunMessageSchema.safeParse(candidate);
    if (parsed.success) {
      const mapped = mapAgentRunMessage(parsed.data);
      this.messagesState.update((messages) => {
        const without = messages.filter((message) => message.id !== mapped.id);
        return [...without, mapped].slice(-MAX_MESSAGES);
      });
      this.setClarificationFromMessage(parsed.data);
    } else if (event.type === 'run.cancelled') {
      this.appendNotice('The backend confirmed that this run was cancelled.', 'Run cancelled');
    } else if (event.type === 'run.failed') {
      this.appendNotice('The run could not be completed. No hidden error details were exposed.', 'Run failed', 'danger');
    }
    this.pendingState.set(false);
    this.connectionState.set('closed');
    this.activeRunIdState.set(null);
    this.cancellationRequestedState.set(false);
    this.watchingStoppedState.set(false);
  }

  private setClarificationFromMessage(message: AgentRunMessage): void {
    if (message.mode !== 'clarification_required') {
      this.clarificationState.set(null);
      return;
    }
    const missing = Array.isArray(message.safe_metadata?.['missing_fields']) ? message.safe_metadata?.['missing_fields'] : [];
    this.clarificationState.set({
      originalRequest: '',
      collectedDetails: [],
      question: message.content,
      missingFields: missing.filter((value): value is string => typeof value === 'string').slice(0,20)
    });
  }

  private recover(): void {
    const conversationId = this.conversationIdState();
    if (!conversationId || !this.organizationId) return;
    this.requestSubscription = this.runApi.conversation(this.organizationId, conversationId).subscribe({
      next: (conversation) => {
        this.messagesState.set(conversation.messages.map(mapAgentRunMessage).slice(-MAX_MESSAGES));
        const last = conversation.messages.at(-1);
        if (last) this.setClarificationFromMessage(last);
        const active = conversation.active_run;
        if (active) {
          if (this.activeRunIdState() !== active.id) {
            this.lastEventSequenceState.set(0);
            this.activitiesState.set([]);
          }
          this.activeRunIdState.set(active.id);
          this.pendingState.set(true);
          this.connect(active.id);
        } else {
          this.activeRunIdState.set(null);
          this.pendingState.set(false);
        }
      },
      error: () => this.clearConversation()
    });
  }

  private submitRest(displayText: string): void {
    if (!this.organizationId) return;
    const clarification = this.pendingClarification();
    const apiQuery = clarification ? composeClarificationQuery(clarification, displayText) : displayText;
    this.lastSubmission = { displayText, apiQuery, clientRequestId: globalThis.crypto?.randomUUID?.() ?? `request-${Date.now()}` };
    this.append(emptyConversationMessage('user', displayText, this.createId(), this.now()));
    this.pendingState.set(true);
    this.requestSubscription = this.restApi.query(this.organizationId, apiQuery).subscribe({
      next: (response) => {
        const mapped = mapAgentResponse(response, this.createId(), this.now());
        this.append(mapped);
        if (response.mode === 'clarification_required') {
          this.clarificationState.set({ originalRequest: clarification?.originalRequest || displayText, collectedDetails:[...(clarification?.collectedDetails ?? []), ...(clarification ? [displayText] : [])].slice(-8), question:response.answer, missingFields:response.missing_fields.slice(0,20) });
        } else this.clarificationState.set(null);
      },
      error: (error: unknown) => {
        this.pendingState.set(false);
        this.requestSubscription = null;
        this.appendError(error, true);
      },
      complete: () => { this.pendingState.set(false); this.requestSubscription = null; }
    });
  }

  private append(message: ConversationMessage): void {
    this.messagesState.update((messages) => [...messages, message].slice(-MAX_MESSAGES));
  }

  private appendError(error: unknown, retryable = false): void {
    if (error instanceof WorkplaceApiError && (error.status === 401 || error.code === 'unauthenticated')) {
      this.currentUser.clearUser();
    }
    const normalized = normalizeWorkplaceError(error);
    const id = this.createId();
    this.append({ ...emptyConversationMessage('error', normalized.message, id, this.now()), tone:'danger', title:normalized.title, retryable: retryable && normalized.retryable });
    this.retryMessageIdState.set(retryable && normalized.retryable ? id : null);
  }

  private appendNotice(text: string, title: string, tone: 'warning' | 'danger' = 'warning'): void {
    this.append({ ...emptyConversationMessage(tone === 'danger' ? 'error' : 'notice', text, this.createId(), this.now()), tone, title });
  }

  private stopAll(): void {
    this.requestSubscription?.unsubscribe();
    this.streamSubscription?.unsubscribe();
    this.streamAbort?.abort();
    this.requestSubscription = null;
    this.streamSubscription = null;
    this.streamAbort = null;
  }

  private now(): string { return new Date().toISOString(); }
  private createId(): string { return globalThis.crypto?.randomUUID?.() ?? `message-${Date.now()}-${Math.random().toString(16).slice(2)}`; }

  private readRecovery(): AgentConversationRecovery | null {
    try {
      const raw = this.document.defaultView?.localStorage?.getItem(STORAGE_KEY)
               ?? this.document.defaultView?.sessionStorage?.getItem(STORAGE_KEY);
      if (!raw) return null;
      const value = JSON.parse(raw) as Partial<AgentConversationRecovery>;
      if (value.version !== 2) return null;
      if (this.scope && value.organizationScope && value.organizationScope !== this.scope) return null;
      return {
        version: 2,
        organizationScope: value.organizationScope ?? this.scope ?? '',
        conversationId: typeof value.conversationId === 'string' ? value.conversationId : null,
        activeRunId: typeof value.activeRunId === 'string' ? value.activeRunId : null,
        lastEventSequence: Number.isInteger(value.lastEventSequence) ? Math.max(0, Number(value.lastEventSequence)) : 0
      };
    } catch { return null; }
  }

  private persistRecovery(): void {
    if (!this.scope || !this.streamingEnabled()) return;
    const convId = this.conversationIdState();
    if (!convId) return;

    const recovery: AgentConversationRecovery = {
      version: 2,
      organizationScope: this.scope,
      conversationId: convId,
      activeRunId: this.activeRunIdState(),
      lastEventSequence: this.lastEventSequenceState(),
    };
    try {
      this.document.defaultView?.localStorage?.setItem(STORAGE_KEY, JSON.stringify(recovery));
      this.document.defaultView?.sessionStorage?.setItem(STORAGE_KEY, JSON.stringify(recovery));
    } catch { /* optional convenience */ }
  }

  private removeRecovery(): void {
    try {
      this.document.defaultView?.localStorage?.removeItem(STORAGE_KEY);
      this.document.defaultView?.sessionStorage?.removeItem(STORAGE_KEY);
    } catch { /* storage may be disabled */ }
  }
}
