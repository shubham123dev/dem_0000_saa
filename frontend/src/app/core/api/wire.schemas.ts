import { z } from 'zod';

export const isoDateTimeSchema = z.iso.datetime({ offset: true });
const nullableDateTime = isoDateTimeSchema.nullable();
const jsonObject = z.record(z.string(), z.unknown());

export const errorEnvelopeSchema = z.object({ error: z.object({ code: z.string().min(1), message: z.string(), request_id: z.string().min(1) }).strict() }).strict();
export const healthSchema = z.object({ status: z.string() }).passthrough();
export const readinessSchema = z.object({ status: z.string(), database: z.string(), environment: z.string() }).passthrough();
export const readinessDetailsSchema = z.object({ status: z.string(), checks: z.record(z.string(), z.boolean()), migration: jsonObject, actions: jsonObject, read_tools: jsonObject, audit: jsonObject, limits: jsonObject, model: jsonObject, raw_mock_api_enabled: z.boolean() }).passthrough();

export const accessSchema = z.object({ user_id: z.string(), permission: z.string() }).strict();
export const organizationSchema = z.object({ id: z.string(), display_name: z.string(), legal_name: z.string().nullable(), contact_email: z.string().nullable(), environment: z.enum(['sandbox','production']), status: z.enum(['active','suspended']), version: z.number().int().nonnegative() }).strict();
export const organizationProfileResponseSchema = z.object({ organization: organizationSchema, access: accessSchema }).strict();
export const organizationOverviewResponseSchema = z.object({ organization: organizationSchema.extend({ organization_type: z.string(), renewal_date: z.iso.date().nullable(), workspace_status: z.enum(['healthy','degraded','unavailable','unknown']) }), metrics: z.object({ licensed_modules:z.number().int().nonnegative(), available_areas:z.number().int().nonnegative(), organization_logins:z.number().int().nonnegative(), workspace_health_percent:z.number().int().min(0).max(100) }), overview_version:z.number().int().positive(), overview_updated_at:nullableDateTime, access:accessSchema, generated_at:isoDateTimeSchema }).strict();

const memberSchema = z.object({ user_id:z.string(), display_name:z.string(), email:z.string(), user_status:z.enum(['active','disabled']), role:z.string(), membership_status:z.enum(['invited','active','suspended','removed']), has_active_seat:z.boolean(), joined_at:nullableDateTime }).strict();
export const organizationUsersResponseSchema = z.object({ organization_id:z.string(), members:z.array(memberSchema), access:accessSchema }).strict();
export const organizationSeatsResponseSchema = z.object({ organization_id:z.string(), seats:z.object({ organization_id:z.string(), seat_type:z.literal('standard'), total_seats:z.number().int().nonnegative(), active_assignments:z.number().int().nonnegative(), available_seats:z.number().int().nonnegative(), seated_user_ids:z.array(z.string()) }).strict(), access:accessSchema }).strict();
const reportSchema = z.object({ id:z.string(), external_report_id:z.string(), title:z.string(), market_name:z.string().nullable(), status:z.enum(['active','retired']) }).strict();
const accessLevel = z.enum(['view','chat','download','full']).nullable();
const reportAccessStatus = z.enum(['active','suspended','expired','revoked']).nullable();
export const organizationReportsResponseSchema = z.object({ organization_id:z.string(), reports:z.array(z.object({ report:reportSchema, has_access:z.boolean(), access_level:accessLevel, access_status:reportAccessStatus }).strict()), access:accessSchema }).strict();
export const reportAccessResponseSchema = z.object({ organization_id:z.string(), report_id:z.string(), has_access:z.boolean(), access_level:accessLevel, access_status:reportAccessStatus, access:accessSchema }).strict();
const auditEventSchema = z.object({ id:z.string(), actor_user_id:z.string(), organization_id:z.string(), event_type:z.string(), operation:z.string(), outcome:z.string(), resource_type:z.string(), resource_id:z.string(), details:jsonObject.nullable(), created_at:nullableDateTime }).strict();
export const auditLogResponseSchema = z.object({ organization_id:z.string(), events:z.array(auditEventSchema) }).strict();

const nucleusAccount = z.object({ organization_account_id:z.number().int(), organization_name:z.string(), organization_code:z.string().nullable(), organization_type:z.string().nullable(), industry:z.string().nullable(), website:z.string().nullable(), login_username:z.string(), email:z.string().nullable(), contact_person_name:z.string().nullable(), contact_person_designation:z.string().nullable(), contact_phone:z.string().nullable(), address_line1:z.string().nullable(), address_line2:z.string().nullable(), city:z.string().nullable(), state:z.string().nullable(), country:z.string().nullable(), postal_code:z.string().nullable(), status:z.string(), is_active:z.boolean(), created_by:z.number().int().nullable(), created_date:isoDateTimeSchema, updated_by:z.number().int().nullable(), updated_date:nullableDateTime, version:z.number().int().positive() }).strict();
export const nucleusAccountResponseSchema = z.object({ organization_id:z.string(), account:nucleusAccount, access:accessSchema, generated_at:isoDateTimeSchema }).strict();
export const nucleusLicenseResponseSchema = z.object({ organization_id:z.string(), license:z.object({ organization_account_id:z.number().int(), max_user_limit:z.number().int().nonnegative(), license_start_date:nullableDateTime, license_end_date:nullableDateTime, is_active:z.boolean(), status:z.string(), version:z.number().int().positive() }).strict(), access:accessSchema, generated_at:isoDateTimeSchema }).strict();
export const nucleusApprovalStatusResponseSchema = z.object({ organization_id:z.string(), approval:z.object({ organization_account_id:z.number().int(), status:z.string(), approved_by:z.number().int().nullable(), approved_date:nullableDateTime, rejected_by:z.number().int().nullable(), rejected_date:nullableDateTime, rejection_reason:z.string().nullable(), is_active:z.boolean(), version:z.number().int().positive() }).strict(), access:accessSchema, generated_at:isoDateTimeSchema }).strict();
const entitlementBase = z.object({ access_id:z.number().int(), organization_account_id:z.number().int(), version:z.number().int().positive() });
export const nucleusEntitlementsResponseSchema = z.object({ organization_id:z.string(), entitlements:z.object({ organization_account_id:z.number().int(), category_access:z.array(entitlementBase.extend({ category_id:z.number().int().nullable(), category_sample_id:z.number().int().nullable(), created_date:nullableDateTime, is_active:z.boolean() }).strict()), company_profile_access:z.array(entitlementBase.extend({ company_id:z.number().int().nullable() }).strict()), drug_access:z.array(entitlementBase.extend({ drug_id:z.number().int().nullable() }).strict()), indication_access:z.array(entitlementBase.extend({ indication_id:z.number().int().nullable() }).strict()), market_access:z.array(entitlementBase.extend({ market_id:z.number().int().nullable(), market_sample_id:z.number().int().nullable() }).strict()), report_access:z.array(entitlementBase.extend({ reports_id:z.number().int().nullable(), sample_id:z.number().int().nullable(), sample_toc_id:z.number().int().nullable(), speciality_id:z.number().int().nullable(), is_executive_access:z.boolean().nullable(), created_date:nullableDateTime, is_active:z.boolean() }).strict()), special_permissions:z.array(z.object({ permission_id:z.number().int(), organization_account_id:z.number().int(), cp_company_master_pharma_id:z.number().int().nullable(), hc_theropetic_category_pharma_id:z.number().int().nullable(), hc_theropetic_category_epidem_id:z.number().int().nullable(), hc_disease_code_epidem_id:z.number().int().nullable(), reports_custom_id:z.number().int().nullable(), importexport_report_id:z.number().int().nullable(), created_date:nullableDateTime, is_active:z.boolean(), version:z.number().int().positive() }).strict()) }).strict(), access:accessSchema, generated_at:isoDateTimeSchema }).strict();

export const agentQueryRequestSchema = z.object({ query:z.string().trim().min(1).max(4000) }).strict();

export const workplaceResourceSearchRequestSchema = z.object({ filters:jsonObject.default({}), sort_by:z.string().max(100).nullable().default(null), descending:z.boolean().default(false), limit:z.number().int().min(1).max(100).default(50), offset:z.number().int().nonnegative().default(0) }).strict();
export const workplaceResourceTypeListResponseSchema = z.object({ resources:z.array(jsonObject) }).strict();
export const workplaceResourceSchemaResponseSchema = z.object({ resource:jsonObject }).strict();
export const workplaceResourceSearchResponseSchema = z.object({ items:z.array(jsonObject), total:z.number().int().nonnegative(), limit:z.number().int().min(1).max(100), offset:z.number().int().nonnegative() }).strict();
export const workplaceResourceCountResponseSchema = z.object({ count:z.number().int().nonnegative() }).strict();
export const workplaceResourceResponseSchema = z.object({ item:jsonObject }).strict();

export const agentActionNameSchema = z.enum([
  'update_organization_contact_email',
  'update_nucleus_organization_account_field',
  'clear_nucleus_organization_account_field',
  'grant_nucleus_category_access',
  'revoke_nucleus_category_access',
  'grant_nucleus_report_access',
  'revoke_nucleus_report_access',
  'update_nucleus_organization_permissions',
  'update_nucleus_organization_username',
  'update_nucleus_organization_license',
  'approve_nucleus_organization_account',
  'reject_nucleus_organization_account',
  'activate_nucleus_organization_account',
  'deactivate_nucleus_organization_account',
  'grant_nucleus_company_profile_access',
  'revoke_nucleus_company_profile_access',
  'grant_nucleus_drug_access',
  'revoke_nucleus_drug_access',
  'grant_nucleus_indication_access',
  'revoke_nucleus_indication_access',
  'grant_nucleus_market_access',
  'revoke_nucleus_market_access',
  'create_workplace_resource',
  'update_workplace_resource',
  'clear_workplace_resource_fields',
  'activate_workplace_resource',
  'deactivate_workplace_resource',
  'delete_workplace_resource',
  'restore_workplace_resource',
  'bulk_update_workplace_resources',
  'invite_organization_user',
  'activate_organization_membership',
  'update_organization_member_role',
  'remove_organization_user',
  'assign_organization_seat',
  'revoke_organization_seat',
  'grant_organization_report_access',
  'revoke_organization_report_access',
  'bulk_update_workplace_resources_by_query',
  'onboard_organization_user',
  'offboard_organization_user',
  'apply_organization_access_package',
  'restore_workplace_resource_snapshots'
]);
export const actionStatusFilterSchema = z.enum(['pending_approval','approved','rejected','expired','cancelled','stale','executing','succeeded','failed','reconciliation_required']);
export const agentActionListFiltersSchema = z.object({
  status: actionStatusFilterSchema.optional(),
  actionName: agentActionNameSchema.optional(),
  requestedBy: z.string().trim().min(1).max(200).optional(),
  limit: z.number().int().min(1).max(200).optional(),
  cursor: z.string().trim().min(1).max(200).optional()
}).strict();
const noArgumentActions = new Set([
  'approve_nucleus_organization_account',
  'activate_nucleus_organization_account',
  'deactivate_nucleus_organization_account'
]);
const actionArgumentsSchema = z.record(z.string(), z.string()).superRefine((value, ctx) => {
  const entries = Object.entries(value);
  if (entries.length > 12) ctx.addIssue({code:'custom',message:'At most 12 action arguments are allowed'});
  for (const [name, argument] of entries) {
    if (!name.trim() || name.length > 100 || !argument.trim() || argument.length > 5000) {
      ctx.addIssue({code:'custom',message:'Action argument names and values must be non-empty and within backend limits'});
      break;
    }
  }
});
export const actionProposalRequestSchema = z.object({
  action_name: agentActionNameSchema,
  arguments: actionArgumentsSchema.default({}),
  contact_email: z.email().min(3).max(320).nullable().optional()
}).strict().superRefine((value, ctx) => {
  if (value.contact_email !== undefined && value.contact_email !== null) {
    if (value.action_name !== 'update_organization_contact_email' || Object.keys(value.arguments).length > 0) {
      ctx.addIssue({code:'custom',message:'contact_email is only valid for update_organization_contact_email'});
    }
  } else if (Object.keys(value.arguments).length === 0 && !noArgumentActions.has(value.action_name)) {
    ctx.addIssue({code:'custom',message:'Action arguments are required'});
  }
});
export const actionDecisionRequestSchema = z.object({ reason:z.string().trim().max(500).nullable().optional() }).strict();
export const actionExecutionRequestSchema = z.object({ idempotency_key:z.string().trim().min(8).max(200) }).strict();

export const actionChangeSchema = z.object({ field:z.string(), before:z.unknown(), after:z.unknown() }).strict();
export const approvalPolicySchema = z.object({ self_approval_allowed:z.boolean(), required_approver_permission:z.string(), minimum_approvals:z.number().int().min(1).max(10) }).strict();
export const actionProposalStatusSchema = z.enum(['pending_approval','approved','rejected','expired','cancelled','stale','executing','succeeded','failed','reconciliation_required']);
export const actionProposalSchema = z.object({ id:z.string(), organization_id:z.string(), requested_by_user_id:z.string(), action_name:z.string(), arguments:z.record(z.string(),z.string()), action_fingerprint:z.string(), fingerprint_version:z.number().int().min(2).max(4), risk_level:z.enum(['low','medium','high']), resource_type:z.string(), resource_id:z.string(), status:actionProposalStatusSchema, changes:z.array(actionChangeSchema), observed_resource_version:z.number().int().nonnegative(), resource_preconditions:z.array(z.object({resource_type:z.string(),resource_id:z.string(),observed_version:z.number().int().nonnegative()}).strict()), approval_policy:approvalPolicySchema, expires_at:isoDateTimeSchema, cancelled_at:nullableDateTime, stale_at:nullableDateTime, created_at:isoDateTimeSchema }).strict();
export const actionProposalResponseSchema = z.object({ proposal:actionProposalSchema, requires_approval:z.boolean(), dry_run:z.boolean() }).strict();
export const actionProposalListResponseSchema = z.object({ proposals:z.array(actionProposalSchema), next_cursor:z.string().nullable() }).strict();
export const actionApprovalResponseSchema = z.object({ approval:z.object({ proposal_id:z.string(), decision:z.enum(['approved','rejected']), decided_by_user_id:z.string(), decision_reason:z.string().nullable(), decided_at:isoDateTimeSchema, consumed_at:nullableDateTime }).strict() }).strict();
export const actionExecutionResponseSchema = z.object({ execution:z.object({ proposal_id:z.string(), idempotency_key:z.string(), executed_by_user_id:z.string(), nucleus_actor_id:z.number().int().nullable(), outcome:z.enum(['executing','succeeded','failed','reconciliation_required']), result:jsonObject.nullable(), error_code:z.string().nullable(), attempt_count:z.number().int().positive(), last_attempt_at:nullableDateTime, provider_operation_id:z.string().nullable(), reconciliation_status:z.string().nullable(), audit_pending:z.boolean(), started_at:isoDateTimeSchema, completed_at:nullableDateTime }).strict() }).strict();
const proposalSummary = z.object({ id:z.string(), action_name:z.string(), risk_level:z.enum(['low','medium','high']), status:z.enum(['pending_approval','approved','rejected','expired','executing','succeeded','failed']), changes:z.array(actionChangeSchema), expires_at:isoDateTimeSchema }).strict();
export const agentQueryResponseSchema = z.object({ mode:z.enum(['read','action_proposal','clarification_required']), organization_id:z.string(), answer:z.string(), evidence_ids:z.array(z.string()), answer_source:z.enum(['model','deterministic']), results:z.array(z.object({tool_name:z.string(),data:z.unknown()}).strict()), action_proposal:proposalSummary.nullable(), missing_fields:z.array(z.string()) }).strict().superRefine((value, ctx) => { if (value.mode === 'read' && (value.action_proposal || value.missing_fields.length)) ctx.addIssue({code:'custom',message:'Invalid read response payload'}); if (value.mode === 'action_proposal' && (!value.action_proposal || value.results.length || value.evidence_ids.length || value.missing_fields.length)) ctx.addIssue({code:'custom',message:'Invalid proposal response payload'}); if (value.mode === 'clarification_required' && (value.action_proposal || value.results.length || value.evidence_ids.length || !value.missing_fields.length)) ctx.addIssue({code:'custom',message:'Invalid clarification response payload'}); });
export const capabilityActionSchema = z.object({ name:z.string(), required_arguments:z.array(z.string()), risk_level:z.string(), requires_approval:z.boolean(), supports_dry_run:z.boolean(), minimum_approvals:z.number().int().positive(), self_approval_allowed:z.boolean(), model_selectable:z.boolean() }).strict();
export const capabilitiesResponseSchema = z.object({ environment:z.string(), read_tools:z.array(z.string()), write_tools:z.array(z.string()), write_actions:z.array(capabilityActionSchema), approval_required:z.boolean(), production_access:z.boolean() }).strict();
