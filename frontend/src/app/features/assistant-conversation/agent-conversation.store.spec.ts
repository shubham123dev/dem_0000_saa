import { DOCUMENT } from '@angular/common';
import { TestBed } from '@angular/core/testing';
import { of, Subject } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { WorkplaceAgentApiService } from '../../core/api/workplace-agent-api.service';
import { APP_RUNTIME_CONFIG } from '../../core/config/app-config.token';
import type { AgentQueryResponse } from '../../core/api/wire.models';
import { AgentConversationStore, composeClarificationQuery } from './agent-conversation.store';

const config = { apiBaseUrl:'/api', defaultOrganizationId:'org_1', mockUserId:'usr_1', requestTimeoutMs:30000, enableDebugViews:false, streamTransport:'rest' as const };
const readResponse: AgentQueryResponse = { mode:'read', organization_id:'org_1', answer:'There are twelve active users.', evidence_ids:['evidence_internal'], answer_source:'model', results:[{tool_name:'internal_tool',data:{count:12}}], action_proposal:null, missing_fields:[] };

describe('AgentConversationStore', () => {
  beforeEach(() => { TestBed.resetTestingModule(); sessionStorage.clear(); });

  it('submits through the single API facade and persists only normalized messages', () => {
    const api = { query: vi.fn(() => of(readResponse)) };
    TestBed.configureTestingModule({ providers:[AgentConversationStore,{provide:WorkplaceAgentApiService,useValue:api},{provide:APP_RUNTIME_CONFIG,useValue:config},{provide:DOCUMENT,useValue:document}] });
    const store=TestBed.inject(AgentConversationStore);
    store.submit('List active users');
    TestBed.tick();
    expect(api.query).toHaveBeenCalledWith('org_1','List active users');
    expect(store.messages().map((message)=>message.role)).toEqual(['user','assistant']);
    const saved=sessionStorage.getItem('dbmr-workplace-conversation-v1') ?? '';
    expect(saved).not.toContain('evidence_internal');
    expect(saved).not.toContain('internal_tool');
    expect(saved).not.toContain('org_1');
  });

  it('sends clarification replies with transparent original-request context', () => {
    const clarification: AgentQueryResponse = { mode:'clarification_required', organization_id:'org_1', answer:'Which report should receive access?', evidence_ids:[], answer_source:'deterministic', results:[], action_proposal:null, missing_fields:['report_id'] };
    const api = { query: vi.fn().mockReturnValueOnce(of(clarification)).mockReturnValueOnce(of(readResponse)) };
    TestBed.configureTestingModule({ providers:[AgentConversationStore,{provide:WorkplaceAgentApiService,useValue:api},{provide:APP_RUNTIME_CONFIG,useValue:config},{provide:DOCUMENT,useValue:document}] });
    const store=TestBed.inject(AgentConversationStore);
    store.submit('Grant report access');
    store.submit('Use the quarterly market report');
    const secondQuery=api.query.mock.calls[1]?.[1] as string;
    expect(secondQuery).toContain('Original request:');
    expect(secondQuery).toContain('Additional details from the user:');
    expect(secondQuery.length).toBeLessThanOrEqual(4000);
  });

  it('stops waiting without claiming the backend operation was cancelled', () => {
    const pending = new Subject<AgentQueryResponse>();
    const api = { query: vi.fn(() => pending.asObservable()) };
    TestBed.configureTestingModule({ providers:[AgentConversationStore,{provide:WorkplaceAgentApiService,useValue:api},{provide:APP_RUNTIME_CONFIG,useValue:config},{provide:DOCUMENT,useValue:document}] });
    const store=TestBed.inject(AgentConversationStore);
    store.submit('Summarize audit activity');
    store.stopWaiting();
    expect(store.pending()).toBe(false);
    expect(store.messages().at(-1)?.text).toContain('backend may still have completed');
  });

  it('keeps composed clarification requests within the backend limit', () => {
    const query=composeClarificationQuery({originalRequest:'x'.repeat(4000),collectedDetails:['y'.repeat(1200)],question:'z'.repeat(4000),missingFields:['report_id']},'r'.repeat(1200));
    expect(query.length).toBeLessThanOrEqual(4000);
  });
});
