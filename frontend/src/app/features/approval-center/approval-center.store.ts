import { computed, DestroyRef, effect, inject, Injectable, signal } from '@angular/core';
import type { Subscription } from 'rxjs';
import { APP_RUNTIME_CONFIG } from '../../core/config/app-config.token';
import { normalizeWorkplaceError } from '../../core/errors/error-normalizer';
import { ActionControlApiService } from '../../core/action-control/action-control-api.service';
import type { ActionConnectionState, ActionExecutionEvent, ActionProposalControl } from '../../core/action-control/action-control.models';
import { ActionExecutionStreamService } from '../../core/action-control/action-execution-stream.service';
import { ActionNavigationStore } from '../../core/action-control/action-navigation.store';

const RECOVERY_KEY = 'dbmr-action-control-recovery-v1';
interface Recovery { proposalId: string; lastSequence: number; executionKey: string | null; }

@Injectable({ providedIn: 'root' })
export class ApprovalCenterStore {
  private readonly config = inject(APP_RUNTIME_CONFIG);
  private readonly api = inject(ActionControlApiService);
  private readonly stream = inject(ActionExecutionStreamService);
  private readonly navigation = inject(ActionNavigationStore);
  private readonly destroyRef = inject(DestroyRef);
  private readonly organizationId = this.config.defaultOrganizationId;
  private readonly proposalsState = signal<ActionProposalControl[]>([]);
  private readonly selectedState = signal<ActionProposalControl | null>(null);
  private readonly eventsState = signal<ActionExecutionEvent[]>([]);
  private readonly loadingState = signal(false);
  private readonly busyState = signal(false);
  private readonly errorState = signal<string | null>(null);
  private readonly statusState = signal('all');
  private readonly searchState = signal('');
  private readonly connectionState = signal<ActionConnectionState>('closed');
  private readonly recovery = this.readRecovery();
  private lastSequence = this.recovery?.lastSequence ?? 0;
  private executionKey = this.recovery?.executionKey ?? null;
  private listRequest?: Subscription;
  private detailRequest?: Subscription;
  private commandRequest?: Subscription;
  private streamSubscription?: Subscription;
  private abort?: AbortController;

  readonly proposals = this.proposalsState.asReadonly();
  readonly selected = this.selectedState.asReadonly();
  readonly events = this.eventsState.asReadonly();
  readonly loading = this.loadingState.asReadonly();
  readonly busy = this.busyState.asReadonly();
  readonly error = this.errorState.asReadonly();
  readonly status = this.statusState.asReadonly();
  readonly search = this.searchState.asReadonly();
  readonly connection = this.connectionState.asReadonly();
  readonly filtered = computed(() => {
    const query = this.search().trim().toLowerCase();
    return this.proposals().filter((proposal) => !query || [proposal.action_label, proposal.resource_label, proposal.requested_by, proposal.status].some((value) => value.toLowerCase().includes(query)));
  });

  constructor() {
    effect(() => {
      const requested = this.navigation.selectedProposalId();
      if (requested) this.select(requested);
    });
    this.destroyRef.onDestroy(() => this.stop());
    this.load();
    if (this.recovery?.proposalId) queueMicrotask(() => this.select(this.recovery!.proposalId, true));
  }

  setStatus(value: string): void { this.statusState.set(value); this.load(); }
  setSearch(value: string): void { this.searchState.set(value); }

  load(): void {
    if (!this.organizationId) return;
    this.loadingState.set(true); this.errorState.set(null);
    this.listRequest?.unsubscribe();
    this.listRequest = this.api.list(this.organizationId, this.status()).subscribe({
      next: (result) => this.proposalsState.set(result.proposals),
      error: (error: unknown) => this.fail(error),
      complete: () => this.loadingState.set(false)
    });
  }

  select(id: string, recover = false): void {
    if (!this.organizationId || (this.selected()?.id === id && !recover)) return;
    this.navigation.open(id); this.errorState.set(null); this.loadingState.set(true);
    this.detailRequest?.unsubscribe();
    this.detailRequest = this.api.detail(this.organizationId, id).subscribe({
      next: (proposal) => {
        this.selectedState.set(proposal);
        if (recover || ['executing', 'reconciliation_required'].includes(proposal.status)) this.watch(proposal.id);
        this.persist();
      },
      error: (error: unknown) => this.fail(error),
      complete: () => this.loadingState.set(false)
    });
  }

  closeDetail(): void {
    const active = this.selected()?.status === 'executing' || this.selected()?.status === 'reconciliation_required';
    if (active) this.persist();
    this.stopStream(); this.selectedState.set(null); this.navigation.clear();
    if (!active) {
      this.lastSequence = 0; this.executionKey = null; this.removeRecovery();
    }
  }

  approve(reason: string | null, confirmation: string | null): void { this.mutate('approve', () => this.api.approve(this.organizationId!, this.requireId(), reason, confirmation)); }
  reject(reason: string | null): void { this.mutate('reject', () => this.api.reject(this.organizationId!, this.requireId(), reason)); }
  cancel(reason: string | null): void { this.mutate('cancel', () => this.api.cancel(this.organizationId!, this.requireId(), reason)); }

  execute(confirmation: string | null): void {
    if (!this.organizationId) return;
    const id = this.requireId();
    this.executionKey ??= globalThis.crypto?.randomUUID?.() ?? `execution-${Date.now()}`;
    this.persist(); this.watch(id); this.busyState.set(true); this.errorState.set(null);
    this.commandRequest?.unsubscribe();
    this.commandRequest = this.api.execute(this.organizationId, id, this.executionKey, confirmation).subscribe({
      next: (proposal) => this.accept(proposal),
      error: (error: unknown) => { this.busyState.set(false); this.fail(error); },
      complete: () => this.busyState.set(false)
    });
  }

  reconcile(): void {
    const id = this.requireId(); this.watch(id);
    this.mutate('reconcile', () => this.api.reconcile(this.organizationId!, id));
  }

  rollback(reason: string | null): void {
    this.mutate('rollback', () => this.api.createRollback(this.organizationId!, this.requireId(), reason), true);
  }

  private mutate(_name: string, request: () => ReturnType<ActionControlApiService['detail']>, selectReturned = false): void {
    if (!this.organizationId || this.busy()) return;
    this.busyState.set(true); this.errorState.set(null);
    this.commandRequest?.unsubscribe();
    this.commandRequest = request().subscribe({
      next: (proposal) => {
        this.accept(proposal);
        if (selectReturned) this.select(proposal.id);
      },
      error: (error: unknown) => { this.busyState.set(false); this.fail(error); },
      complete: () => this.busyState.set(false)
    });
  }

  private accept(proposal: ActionProposalControl): void {
    this.selectedState.set(proposal);
    this.proposalsState.update((items) => {
      const next = items.filter((item) => item.id !== proposal.id);
      return [proposal, ...next];
    });
    if (proposal.execution && ['succeeded', 'failed', 'reconciliation_required'].includes(proposal.execution.outcome)) {
      if (proposal.execution.outcome !== 'reconciliation_required') this.executionKey = null;
    }
    this.persist();
  }

  private watch(proposalId: string): void {
    if (!this.organizationId) return;
    this.stopStream(); this.abort = new AbortController();
    this.streamSubscription = this.stream.watch(this.organizationId, proposalId, this.lastSequence, this.abort.signal).subscribe({
      next: (update) => {
        if (update.kind === 'state') { this.connectionState.set(update.state); return; }
        if (update.event.sequence <= this.lastSequence) return;
        this.lastSequence = update.event.sequence;
        this.eventsState.update((events) => [...events.filter((event) => event.sequence !== update.event.sequence), update.event].sort((a,b) => a.sequence-b.sequence).slice(-50));
        this.persist();
        if (update.event.terminal) this.refreshSelected();
      },
      error: (error: unknown) => { this.connectionState.set('closed'); this.fail(error); },
      complete: () => this.connectionState.set('closed')
    });
  }

  private refreshSelected(): void { const id = this.selected()?.id; if (id && this.organizationId) this.api.detail(this.organizationId, id).subscribe({ next: (proposal) => this.accept(proposal) }); }
  private requireId(): string { const id = this.selected()?.id; if (!id) throw new Error('No action proposal is selected.'); return id; }
  private fail(error: unknown): void { const normalized = normalizeWorkplaceError(error); this.errorState.set(`${normalized.title}: ${normalized.message}`); this.loadingState.set(false); }
  private stopStream(): void { this.streamSubscription?.unsubscribe(); this.abort?.abort(); this.streamSubscription=undefined; this.abort=undefined; this.connectionState.set('closed'); }
  private stop(): void {
    this.listRequest?.unsubscribe();
    this.detailRequest?.unsubscribe();
    this.commandRequest?.unsubscribe();
    this.stopStream();
  }
  private persist(): void { const id=this.selected()?.id; if(!id) return; try { sessionStorage.setItem(RECOVERY_KEY, JSON.stringify({ proposalId:id, lastSequence:this.lastSequence, executionKey:this.executionKey } satisfies Recovery)); } catch { /* optional */ } }
  private readRecovery(): Recovery | null { try { const raw=sessionStorage.getItem(RECOVERY_KEY); if(!raw) return null; const value=JSON.parse(raw) as Partial<Recovery>; return typeof value.proposalId==='string' ? {proposalId:value.proposalId,lastSequence:Number.isInteger(value.lastSequence)?Number(value.lastSequence):0,executionKey:typeof value.executionKey==='string'?value.executionKey:null}:null; } catch { return null; } }
  private removeRecovery(): void { try { sessionStorage.removeItem(RECOVERY_KEY); } catch { /* optional */ } }
}
