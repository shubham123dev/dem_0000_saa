import { inject, Injectable } from '@angular/core';
import type { Observable } from 'rxjs';
import { map } from 'rxjs';
import { AuthenticatedSseClient } from '../sse/authenticated-sse-client.service';
import type { ActionExecutionStreamUpdate } from './action-control.models';
import { actionExecutionEventSchema } from './action-control.schemas';

function encode(value: string): string { return encodeURIComponent(value); }

@Injectable({ providedIn: 'root' })
export class ActionExecutionStreamService {
  private readonly client = inject(AuthenticatedSseClient);

  watch(organizationId: string, proposalId: string, afterSequence: number, signal?: AbortSignal): Observable<ActionExecutionStreamUpdate> {
    const path = `/workplace/organizations/${encode(organizationId)}/agent/control/actions/${encode(proposalId)}/execution/events`;
    return this.client.watch(path, actionExecutionEventSchema, afterSequence, signal).pipe(
      map((update) => update.kind === 'state'
        ? { kind: 'state' as const, state: update.state }
        : { kind: 'event' as const, event: update.event })
    );
  }
}
