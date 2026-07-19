import { DOCUMENT } from '@angular/common';
import { inject, Injectable, signal } from '@angular/core';
import { catchError, finalize, tap, throwError, type Observable, type Subscription } from 'rxjs';
import { APP_RUNTIME_CONFIG } from '../config/app-config.token';
import { normalizeWorkplaceError } from '../errors/error-normalizer';
import { ActionControlApiService } from './action-control-api.service';
import type { ActionProposalControl } from './action-control.models';

const CONVERSATION_RECOVERY_KEY = 'dbmr-workplace-conversation-v2';

@Injectable()
export class ProposalControlFacade {
  private readonly document = inject(DOCUMENT);
  private readonly config = inject(APP_RUNTIME_CONFIG);
  private readonly api = inject(ActionControlApiService);
  private readonly organizationId = this.config.defaultOrganizationId;
  private readonly proposalState = signal<ActionProposalControl | null>(null);
  private readonly loadingState = signal(false);
  private readonly busyState = signal(false);
  private readonly errorState = signal<string | null>(null);
  private loadRequest?: Subscription;

  readonly proposal = this.proposalState.asReadonly();
  readonly loading = this.loadingState.asReadonly();
  readonly busy = this.busyState.asReadonly();
  readonly error = this.errorState.asReadonly();

  load(proposalId: string | null): void {
    if (!this.organizationId) return;
    const request = proposalId
      ? this.api.detail(this.organizationId, proposalId)
      : this.conversationId()
        ? this.api.forConversation(this.organizationId, this.conversationId()!)
        : null;
    if (!request) return;
    this.loadingState.set(true);
    this.errorState.set(null);
    this.loadRequest?.unsubscribe();
    this.loadRequest = request.pipe(finalize(() => this.loadingState.set(false))).subscribe({
      next: (proposal) => this.proposalState.set(proposal),
      error: (error: unknown) => this.setError(error)
    });
  }

  approve(reason: string | null, confirmation: string | null): Observable<ActionProposalControl> {
    return this.command((organizationId, proposalId) => this.api.approve(organizationId, proposalId, reason, confirmation));
  }

  reject(reason: string | null): Observable<ActionProposalControl> {
    return this.command((organizationId, proposalId) => this.api.reject(organizationId, proposalId, reason));
  }

  refresh(): void {
    this.load(this.proposal()?.id ?? null);
  }

  private command(factory: (organizationId: string, proposalId: string) => Observable<ActionProposalControl>): Observable<ActionProposalControl> {
    const proposalId = this.proposal()?.id;
    if (!this.organizationId || !proposalId) return throwError(() => new Error('No authoritative proposal is available.'));
    this.busyState.set(true);
    this.errorState.set(null);
    return factory(this.organizationId, proposalId).pipe(
      tap((proposal) => this.proposalState.set(proposal)),
      catchError((error: unknown) => {
        this.setError(error);
        this.load(proposalId);
        return throwError(() => error);
      }),
      finalize(() => this.busyState.set(false))
    );
  }

  private setError(error: unknown): void {
    const normalized = normalizeWorkplaceError(error);
    this.errorState.set(`${normalized.title}: ${normalized.message}`);
  }

  private conversationId(): string | null {
    try {
      const raw = this.document.defaultView?.sessionStorage.getItem(CONVERSATION_RECOVERY_KEY);
      if (!raw) return null;
      const value = JSON.parse(raw) as { conversationId?: unknown };
      return typeof value.conversationId === 'string' ? value.conversationId : null;
    } catch {
      return null;
    }
  }
}
