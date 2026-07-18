import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';
import { describe, expect, it } from 'vitest';
import { authHeaderInterceptor } from '../auth/auth-header.interceptor';
import { APP_RUNTIME_CONFIG } from '../config/app-config.token';
import { WorkplaceAgentApiService } from './workplace-agent-api.service';

describe('WorkplaceAgentApiService', () => {
  it('uses the canonical query route and auth interceptor', async () => {
    TestBed.configureTestingModule({ providers:[
      {provide:APP_RUNTIME_CONFIG,useValue:{apiBaseUrl:'/api',defaultOrganizationId:'org_1',mockUserId:'usr_1',requestTimeoutMs:30000,enableDebugViews:false,streamTransport:'rest'}},
      provideHttpClient(withInterceptors([authHeaderInterceptor])), provideHttpClientTesting()
    ]});
    const service=TestBed.inject(WorkplaceAgentApiService); const http=TestBed.inject(HttpTestingController);
    const promise=firstValueFrom(service.query('org 1','  hello  '));
    const req=http.expectOne('/api/workplace/organizations/org%201/agent/query');
    expect(req.request.headers.get('X-Mock-User-Id')).toBe('usr_1');
    expect(req.request.body).toEqual({query:'hello'});
    req.flush({mode:'read',organization_id:'org 1',answer:'Hello',evidence_ids:[],answer_source:'deterministic',results:[],action_proposal:null,missing_fields:[]});
    expect((await promise).answer).toBe('Hello'); http.verify();
  });

  it('rejects query and proposal-list inputs outside backend limits', () => {
    TestBed.configureTestingModule({ providers:[
      {provide:APP_RUNTIME_CONFIG,useValue:{apiBaseUrl:'/api',defaultOrganizationId:'org_1',mockUserId:'usr_1',requestTimeoutMs:30000,enableDebugViews:false,streamTransport:'rest'}},
      provideHttpClient(withInterceptors([authHeaderInterceptor])), provideHttpClientTesting()
    ]});
    const service=TestBed.inject(WorkplaceAgentApiService);
    expect(() => service.query('org_1','x'.repeat(4001))).toThrow();
    expect(() => service.listProposals('org_1',{limit:201})).toThrow();
  });
});
