import { inject, Injectable } from '@angular/core';
import type { Observable } from 'rxjs';
import { ValidatedHttpService } from '../api/validated-http.service';
import type { ActionCapabilityCatalogue, ActionProposalControl, ActionProposalControlList } from './action-control.models';
import { actionCapabilityCatalogueSchema, actionProposalControlListSchema, actionProposalControlSchema } from './action-control.schemas';

function encode(value: string): string { return encodeURIComponent(value); }
function root(organizationId: string): string { return `/workplace/organizations/${encode(organizationId)}/agent`; }

@Injectable({ providedIn: 'root' })
export class ActionControlApiService {
  private readonly client = inject(ValidatedHttpService);

  capabilities(organizationId: string): Observable<ActionCapabilityCatalogue> {
    return this.client.request('GET', `${root(organizationId)}/capabilities`, actionCapabilityCatalogueSchema);
  }

  list(organizationId: string, status?: string): Observable<ActionProposalControlList> {
    const query = status && status !== 'all' ? `?status=${encode(status)}` : '';
    return this.client.request('GET', `${root(organizationId)}/control/actions${query}`, actionProposalControlListSchema);
  }

  detail(organizationId: string, proposalId: string): Observable<ActionProposalControl> {
    return this.client.request('GET', `${root(organizationId)}/control/actions/${encode(proposalId)}`, actionProposalControlSchema);
  }

  forConversation(organizationId: string, conversationId: string): Observable<ActionProposalControl> {
    return this.client.request('GET', `${root(organizationId)}/control/conversations/${encode(conversationId)}/action`, actionProposalControlSchema);
  }

  approve(organizationId: string, proposalId: string, reason: string | null, confirmation: string | null): Observable<ActionProposalControl> {
    return this.command(organizationId, proposalId, 'approve', { reason, confirmation });
  }

  reject(organizationId: string, proposalId: string, reason: string | null): Observable<ActionProposalControl> {
    return this.command(organizationId, proposalId, 'reject', { reason, confirmation: null });
  }

  cancel(organizationId: string, proposalId: string, reason: string | null): Observable<ActionProposalControl> {
    return this.command(organizationId, proposalId, 'cancel', { reason, confirmation: null });
  }

  execute(organizationId: string, proposalId: string, idempotencyKey: string, confirmation: string | null): Observable<ActionProposalControl> {
    return this.command(organizationId, proposalId, 'execute', { idempotency_key: idempotencyKey, confirmation });
  }

  reconcile(organizationId: string, proposalId: string): Observable<ActionProposalControl> {
    return this.command(organizationId, proposalId, 'reconcile', undefined);
  }

  createRollback(organizationId: string, proposalId: string, reason: string | null): Observable<ActionProposalControl> {
    return this.command(organizationId, proposalId, 'rollback-proposal', { reason, confirmation: null });
  }

  private command(organizationId: string, proposalId: string, command: string, body: unknown): Observable<ActionProposalControl> {
    return this.client.request('POST', `${root(organizationId)}/control/actions/${encode(proposalId)}/${command}`, actionProposalControlSchema, body === undefined ? undefined : { body });
  }
}
