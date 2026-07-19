import { z } from 'zod';
import { isoDateTimeSchema } from '../api/wire.schemas';

export const actionRiskSchema = z.enum(['low', 'medium', 'high']);
export const actionAllowedOperationsSchema = z.object({
  approve: z.boolean(), reject: z.boolean(), cancel: z.boolean(),
  execute: z.boolean(), reconcile: z.boolean(), create_rollback: z.boolean()
}).strict();

export const actionControlChangeSchema = z.object({
  field: z.string().min(1).max(160),
  before: z.string().max(180),
  after: z.string().max(180)
}).strict();

export const actionApprovalProgressSchema = z.object({
  approved: z.number().int().nonnegative(),
  required: z.number().int().positive(),
  complete: z.boolean()
}).strict();

export const actionExecutionReceiptSchema = z.object({
  outcome: z.enum(['executing', 'succeeded', 'failed', 'reconciliation_required']),
  resource_label: z.string().min(1).max(160),
  before: z.record(z.string(), z.unknown()).nullable(),
  after: z.record(z.string(), z.unknown()).nullable(),
  error_code: z.string().nullable(),
  started_at: isoDateTimeSchema,
  completed_at: isoDateTimeSchema.nullable(),
  executed_by: z.string().min(1).max(200),
  rollback_available: z.boolean()
}).strict();

export const actionProposalControlSchema = z.object({
  id: z.string().min(1),
  action_name: z.string().min(1),
  action_label: z.string().min(1).max(200),
  resource_label: z.string().min(1).max(200),
  status: z.string().min(1).max(80),
  risk_level: actionRiskSchema,
  requested_by: z.string().min(1).max(200),
  created_at: isoDateTimeSchema,
  expires_at: isoDateTimeSchema,
  approval_progress: actionApprovalProgressSchema,
  self_approval_allowed: z.boolean(),
  required_approver_permission: z.string().min(1).max(200),
  changes: z.array(actionControlChangeSchema).max(20),
  allowed_operations: actionAllowedOperationsSchema,
  source_conversation_id: z.string().nullable(),
  execution: actionExecutionReceiptSchema.nullable()
}).strict();

export const actionProposalControlListSchema = z.object({
  proposals: z.array(actionProposalControlSchema).max(200),
  next_cursor: z.string().nullable()
}).strict();

export const actionCapabilitySchema = z.object({
  name: z.string().min(1), label: z.string().min(1), description: z.string(),
  resource_label: z.string().min(1), risk_level: actionRiskSchema,
  requires_approval: z.boolean(), supports_dry_run: z.boolean(), available: z.boolean()
}).strict();
export const actionCapabilityCatalogueSchema = z.object({
  action_capabilities: z.array(actionCapabilitySchema).max(100),
  lifecycle: z.array(z.string()).max(12)
}).strict();

export const actionExecutionEventSchema = z.object({
  schema_version: z.literal(1),
  proposal_id: z.string().min(1),
  sequence: z.number().int().positive(),
  type: z.string().min(1).max(80),
  stage: z.string().min(1).max(80),
  message: z.string().min(1).max(240),
  payload: z.record(z.string(), z.unknown()).nullable(),
  terminal: z.boolean(),
  occurred_at: isoDateTimeSchema
}).strict();
