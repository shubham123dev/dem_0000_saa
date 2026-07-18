import type { z } from 'zod';
import type {
  actionApprovalResponseSchema, agentActionListFiltersSchema, agentQueryRequestSchema, actionDecisionRequestSchema, actionExecutionRequestSchema, actionExecutionResponseSchema, actionProposalListResponseSchema, actionProposalRequestSchema, actionProposalResponseSchema,
  agentQueryResponseSchema, auditLogResponseSchema, capabilitiesResponseSchema, healthSchema, nucleusAccountResponseSchema,
  nucleusApprovalStatusResponseSchema, nucleusEntitlementsResponseSchema, nucleusLicenseResponseSchema, organizationOverviewResponseSchema,
  organizationProfileResponseSchema, organizationReportsResponseSchema, organizationSeatsResponseSchema, organizationUsersResponseSchema,
  readinessDetailsSchema, readinessSchema, reportAccessResponseSchema, workplaceResourceCountResponseSchema, workplaceResourceResponseSchema,
  workplaceResourceSchemaResponseSchema, workplaceResourceSearchRequestSchema, workplaceResourceSearchResponseSchema, workplaceResourceTypeListResponseSchema
} from './wire.schemas';

export type HealthResponse = z.infer<typeof healthSchema>;
export type ReadinessResponse = z.infer<typeof readinessSchema>;
export type ReadinessDetailsResponse = z.infer<typeof readinessDetailsSchema>;
export type CapabilitiesResponse = z.infer<typeof capabilitiesResponseSchema>;
export type OrganizationOverviewResponse = z.infer<typeof organizationOverviewResponseSchema>;
export type OrganizationProfileResponse = z.infer<typeof organizationProfileResponseSchema>;
export type OrganizationUsersResponse = z.infer<typeof organizationUsersResponseSchema>;
export type OrganizationSeatsResponse = z.infer<typeof organizationSeatsResponseSchema>;
export type OrganizationReportsResponse = z.infer<typeof organizationReportsResponseSchema>;
export type ReportAccessResponse = z.infer<typeof reportAccessResponseSchema>;
export type AuditLogResponse = z.infer<typeof auditLogResponseSchema>;
export type NucleusAccountResponse = z.infer<typeof nucleusAccountResponseSchema>;
export type NucleusLicenseResponse = z.infer<typeof nucleusLicenseResponseSchema>;
export type NucleusApprovalStatusResponse = z.infer<typeof nucleusApprovalStatusResponseSchema>;
export type NucleusEntitlementsResponse = z.infer<typeof nucleusEntitlementsResponseSchema>;
export type WorkplaceResourceSearchRequest = z.input<typeof workplaceResourceSearchRequestSchema>;
export type WorkplaceResourceTypeListResponse = z.infer<typeof workplaceResourceTypeListResponseSchema>;
export type WorkplaceResourceSchemaResponse = z.infer<typeof workplaceResourceSchemaResponseSchema>;
export type WorkplaceResourceSearchResponse = z.infer<typeof workplaceResourceSearchResponseSchema>;
export type WorkplaceResourceCountResponse = z.infer<typeof workplaceResourceCountResponseSchema>;
export type WorkplaceResourceResponse = z.infer<typeof workplaceResourceResponseSchema>;
export type AgentQueryRequest = z.input<typeof agentQueryRequestSchema>;
export type AgentQueryResponse = z.infer<typeof agentQueryResponseSchema>;
export type AgentActionProposalResponse = z.infer<typeof actionProposalResponseSchema>;
export type AgentActionProposalListResponse = z.infer<typeof actionProposalListResponseSchema>;
export type AgentActionApprovalResponse = z.infer<typeof actionApprovalResponseSchema>;
export type AgentActionExecutionResponse = z.infer<typeof actionExecutionResponseSchema>;

export type AgentActionProposalRequest = z.input<typeof actionProposalRequestSchema>;
export type AgentActionDecisionRequest = z.input<typeof actionDecisionRequestSchema>;
export type AgentActionExecutionRequest = z.input<typeof actionExecutionRequestSchema>;
export type AgentActionListFilters = z.input<typeof agentActionListFiltersSchema>;
