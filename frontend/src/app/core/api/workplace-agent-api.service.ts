import { HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import type { Observable } from 'rxjs';
import { ValidatedHttpService } from './validated-http.service';
import type {
  AgentActionApprovalResponse, AgentActionDecisionRequest, AgentActionExecutionRequest, AgentActionExecutionResponse,
  AgentActionListFilters, AgentActionProposalListResponse, AgentActionProposalRequest, AgentActionProposalResponse, AgentQueryResponse,
  AuditLogResponse, CapabilitiesResponse, HealthResponse, NucleusAccountResponse, NucleusApprovalStatusResponse,
  NucleusEntitlementsResponse, NucleusLicenseResponse, OrganizationOverviewResponse, OrganizationProfileResponse,
  OrganizationReportsResponse, OrganizationSeatsResponse, OrganizationUsersResponse, ReadinessDetailsResponse, ReadinessResponse,
  ReportAccessResponse, WorkplaceResourceCountResponse, WorkplaceResourceResponse, WorkplaceResourceSchemaResponse,
  WorkplaceResourceSearchRequest, WorkplaceResourceSearchResponse, WorkplaceResourceTypeListResponse
} from './wire.models';
import {
  actionApprovalResponseSchema, actionDecisionRequestSchema, actionExecutionRequestSchema, actionExecutionResponseSchema, actionProposalListResponseSchema, actionProposalRequestSchema, actionProposalResponseSchema,
  agentQueryResponseSchema, auditLogResponseSchema, capabilitiesResponseSchema, healthSchema, nucleusAccountResponseSchema,
  nucleusApprovalStatusResponseSchema, nucleusEntitlementsResponseSchema, nucleusLicenseResponseSchema, organizationOverviewResponseSchema,
  organizationProfileResponseSchema, organizationReportsResponseSchema, organizationSeatsResponseSchema, organizationUsersResponseSchema,
  readinessDetailsSchema, readinessSchema, reportAccessResponseSchema, workplaceResourceCountResponseSchema, workplaceResourceResponseSchema,
  workplaceResourceSchemaResponseSchema, workplaceResourceSearchRequestSchema, workplaceResourceSearchResponseSchema, workplaceResourceTypeListResponseSchema
} from './wire.schemas';

function encode(value: string): string { return encodeURIComponent(value); }
function orgPath(organizationId: string): string { return `/workplace/organizations/${encode(organizationId)}`; }

@Injectable({ providedIn: 'root' })
export class WorkplaceAgentApiService {
  private readonly client = inject(ValidatedHttpService);

  health(): Observable<HealthResponse> { return this.client.request('GET','/health',healthSchema); }
  readiness(): Observable<ReadinessResponse> { return this.client.request('GET','/ready',readinessSchema); }
  readinessDetails(): Observable<ReadinessDetailsResponse> { return this.client.request('GET','/ready/details',readinessDetailsSchema); }
  capabilities(): Observable<CapabilitiesResponse> { return this.client.request('GET','/workplace/capabilities',capabilitiesResponseSchema); }
  organizationOverview(id:string):Observable<OrganizationOverviewResponse>{ return this.client.request('GET',`${orgPath(id)}/overview`,organizationOverviewResponseSchema); }
  organizationProfile(id:string):Observable<OrganizationProfileResponse>{ return this.client.request('GET',`${orgPath(id)}/profile`,organizationProfileResponseSchema); }
  organizationUsers(id:string):Observable<OrganizationUsersResponse>{ return this.client.request('GET',`${orgPath(id)}/users`,organizationUsersResponseSchema); }
  organizationSeats(id:string):Observable<OrganizationSeatsResponse>{ return this.client.request('GET',`${orgPath(id)}/seats`,organizationSeatsResponseSchema); }
  organizationReports(id:string):Observable<OrganizationReportsResponse>{ return this.client.request('GET',`${orgPath(id)}/reports`,organizationReportsResponseSchema); }
  reportAccess(id:string,reportId:string):Observable<ReportAccessResponse>{ return this.client.request('GET',`${orgPath(id)}/reports/${encode(reportId)}/access`,reportAccessResponseSchema); }
  auditLog(id:string):Observable<AuditLogResponse>{ return this.client.request('GET',`${orgPath(id)}/audit-log`,auditLogResponseSchema); }
  nucleusAccount(id:string):Observable<NucleusAccountResponse>{ return this.client.request('GET',`${orgPath(id)}/nucleus/account`,nucleusAccountResponseSchema); }
  nucleusLicense(id:string):Observable<NucleusLicenseResponse>{ return this.client.request('GET',`${orgPath(id)}/nucleus/license`,nucleusLicenseResponseSchema); }
  nucleusApprovalStatus(id:string):Observable<NucleusApprovalStatusResponse>{ return this.client.request('GET',`${orgPath(id)}/nucleus/approval-status`,nucleusApprovalStatusResponseSchema); }
  nucleusEntitlements(id:string):Observable<NucleusEntitlementsResponse>{ return this.client.request('GET',`${orgPath(id)}/nucleus/entitlements`,nucleusEntitlementsResponseSchema); }
  resourceTypes(id:string):Observable<WorkplaceResourceTypeListResponse>{ return this.client.request('GET',`${orgPath(id)}/resources`,workplaceResourceTypeListResponseSchema); }
  resourceSchema(id:string,type:string):Observable<WorkplaceResourceSchemaResponse>{ return this.client.request('GET',`${orgPath(id)}/resources/${encode(type)}/schema`,workplaceResourceSchemaResponseSchema); }
  searchResources(id:string,type:string,request:WorkplaceResourceSearchRequest):Observable<WorkplaceResourceSearchResponse>{ const body=workplaceResourceSearchRequestSchema.parse(request); return this.client.request('POST',`${orgPath(id)}/resources/${encode(type)}/search`,workplaceResourceSearchResponseSchema,{body}); }
  countResources(id:string,type:string,request:WorkplaceResourceSearchRequest):Observable<WorkplaceResourceCountResponse>{ const body=workplaceResourceSearchRequestSchema.parse(request); return this.client.request('POST',`${orgPath(id)}/resources/${encode(type)}/count`,workplaceResourceCountResponseSchema,{body}); }
  resource(id:string,type:string,resourceId:string):Observable<WorkplaceResourceResponse>{ return this.client.request('GET',`${orgPath(id)}/resources/${encode(type)}/${encode(resourceId)}`,workplaceResourceResponseSchema); }
  query(id:string,query:string):Observable<AgentQueryResponse>{ const normalized=query.trim(); if(!normalized) throw new Error('Query must not be empty.'); return this.client.request('POST',`${orgPath(id)}/agent/query`,agentQueryResponseSchema,{body:{query:normalized}}); }
  propose(id:string,request:AgentActionProposalRequest):Observable<AgentActionProposalResponse>{ const body=actionProposalRequestSchema.parse(request); return this.client.request('POST',`${orgPath(id)}/agent/actions/propose`,actionProposalResponseSchema,{body}); }
  listProposals(id:string,filters:AgentActionListFilters={}):Observable<AgentActionProposalListResponse>{ let params=new HttpParams(); if(filters.status)params=params.set('status',filters.status); if(filters.actionName)params=params.set('action_name',filters.actionName); if(filters.requestedBy)params=params.set('requested_by',filters.requestedBy); if(filters.limit)params=params.set('limit',String(filters.limit)); if(filters.cursor)params=params.set('cursor',filters.cursor); return this.client.request('GET',`${orgPath(id)}/agent/actions`,actionProposalListResponseSchema,{params}); }
  proposal(id:string,proposalId:string):Observable<AgentActionProposalResponse>{ return this.client.request('GET',`${orgPath(id)}/agent/actions/${encode(proposalId)}`,actionProposalResponseSchema); }
  approve(id:string,proposalId:string,request:AgentActionDecisionRequest={}):Observable<AgentActionApprovalResponse>{ return this.decision(id,proposalId,'approve',request); }
  reject(id:string,proposalId:string,request:AgentActionDecisionRequest={}):Observable<AgentActionApprovalResponse>{ return this.decision(id,proposalId,'reject',request); }
  cancel(id:string,proposalId:string,request:AgentActionDecisionRequest={}):Observable<AgentActionProposalResponse>{ const body=actionDecisionRequestSchema.parse(request); return this.client.request('POST',`${orgPath(id)}/agent/actions/${encode(proposalId)}/cancel`,actionProposalResponseSchema,{body}); }
  createRollbackProposal(id:string,proposalId:string,request:AgentActionDecisionRequest={}):Observable<AgentActionProposalResponse>{ const body=actionDecisionRequestSchema.parse(request); return this.client.request('POST',`${orgPath(id)}/agent/actions/${encode(proposalId)}/rollback-proposal`,actionProposalResponseSchema,{body}); }
  execute(id:string,proposalId:string,request:AgentActionExecutionRequest):Observable<AgentActionExecutionResponse>{ const body=actionExecutionRequestSchema.parse(request); return this.client.request('POST',`${orgPath(id)}/agent/actions/${encode(proposalId)}/execute`,actionExecutionResponseSchema,{body}); }
  reconcile(id:string,proposalId:string):Observable<AgentActionExecutionResponse>{ return this.client.request('POST',`${orgPath(id)}/agent/actions/${encode(proposalId)}/reconcile`,actionExecutionResponseSchema); }
  replayAudit(id:string,proposalId:string):Observable<AgentActionExecutionResponse>{ return this.client.request('POST',`${orgPath(id)}/agent/actions/${encode(proposalId)}/audit-replay`,actionExecutionResponseSchema); }
  private decision(id:string,proposalId:string,kind:'approve'|'reject',request:AgentActionDecisionRequest):Observable<AgentActionApprovalResponse>{ const body=actionDecisionRequestSchema.parse(request); return this.client.request('POST',`${orgPath(id)}/agent/actions/${encode(proposalId)}/${kind}`,actionApprovalResponseSchema,{body}); }
}
