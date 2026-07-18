import { inject, Injectable } from '@angular/core';
import type { Observable } from 'rxjs';
import { ValidatedHttpService } from '../api/validated-http.service';
import type {
  AgentConversationResponse,
  AgentRun,
  AgentRunCreateRequest,
  AgentRunCreateResponse
} from './agent-run.models';
import {
  agentConversationResponseSchema,
  agentRunCreateRequestSchema,
  agentRunCreateResponseSchema,
  agentRunSchema
} from './agent-run.schemas';

function encode(value: string): string { return encodeURIComponent(value); }
function base(organizationId: string): string {
  return `/workplace/organizations/${encode(organizationId)}/agent`;
}

@Injectable({ providedIn: 'root' })
export class AgentRunApiService {
  private readonly client = inject(ValidatedHttpService);

  create(
    organizationId: string,
    request: AgentRunCreateRequest
  ): Observable<AgentRunCreateResponse> {
    const body = agentRunCreateRequestSchema.parse(request);
    return this.client.request(
      'POST', `${base(organizationId)}/runs`, agentRunCreateResponseSchema, { body }
    );
  }

  conversation(
    organizationId: string,
    conversationId: string
  ): Observable<AgentConversationResponse> {
    return this.client.request(
      'GET',
      `${base(organizationId)}/conversations/${encode(conversationId)}`,
      agentConversationResponseSchema
    );
  }

  run(organizationId: string, runId: string): Observable<AgentRun> {
    return this.client.request(
      'GET', `${base(organizationId)}/runs/${encode(runId)}`, agentRunSchema
    );
  }

  cancel(organizationId: string, runId: string): Observable<AgentRun> {
    return this.client.request(
      'POST', `${base(organizationId)}/runs/${encode(runId)}/cancel`, agentRunSchema
    );
  }
}
