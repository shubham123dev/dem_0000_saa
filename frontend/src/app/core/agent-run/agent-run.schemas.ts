import { z } from 'zod';
import { isoDateTimeSchema } from '../api/wire.schemas';

export const agentRunStatusSchema = z.enum([
  'queued', 'running', 'cancel_requested', 'succeeded',
  'clarification_required', 'proposal_ready', 'failed', 'cancelled'
]);

export const agentRunMessageSchema = z.object({
  id: z.string().min(1),
  sequence: z.number().int().positive(),
  role: z.enum(['user', 'assistant']),
  content: z.string().max(8000),
  mode: z.enum(['read', 'action_proposal', 'clarification_required']).nullable(),
  answer_source: z.enum(['model', 'deterministic']).nullable(),
  safe_metadata: z.record(z.string(), z.unknown()).nullable(),
  created_at: isoDateTimeSchema
}).strict();

export const agentRunSchema = z.object({
  id: z.string().min(1),
  conversation_id: z.string().min(1),
  status: agentRunStatusSchema,
  current_stage: z.string().min(1),
  final_mode: z.string().nullable(),
  error_code: z.string().nullable(),
  cancellation_requested_at: isoDateTimeSchema.nullable(),
  attempt_count: z.number().int().nonnegative(),
  terminal: z.boolean(),
  created_at: isoDateTimeSchema,
  started_at: isoDateTimeSchema.nullable(),
  completed_at: isoDateTimeSchema.nullable()
}).strict();

export const agentRunCreateRequestSchema = z.object({
  query: z.string().trim().min(1).max(4000),
  client_request_id: z.string().trim().min(8).max(64),
  conversation_id: z.string().min(1).max(64).nullable()
}).strict();

export const agentRunCreateResponseSchema = z.object({
  conversation_id: z.string().min(1),
  run: agentRunSchema,
  user_message: agentRunMessageSchema,
  events_url: z.string().startsWith('/'),
  created: z.boolean()
}).strict();

export const agentConversationResponseSchema = z.object({
  conversation_id: z.string().min(1),
  messages: z.array(agentRunMessageSchema).max(100),
  active_run: agentRunSchema.nullable()
}).strict();

export const agentRunEventSchema = z.object({
  schema_version: z.literal(1),
  run_id: z.string().min(1),
  sequence: z.number().int().positive(),
  type: z.enum([
    'run.accepted', 'run.started', 'activity.updated',
    'clarification.required', 'proposal.created', 'answer.completed',
    'run.cancel_requested', 'run.cancelled', 'run.failed'
  ]),
  stage: z.enum([
    'request_acceptance', 'access_check', 'request_planning', 'data_retrieval',
    'proposal_preparation', 'answer_preparation', 'external_wait',
    'verification', 'completion'
  ]),
  message: z.string().min(1).max(240),
  payload: z.record(z.string(), z.unknown()).nullable(),
  terminal: z.boolean(),
  occurred_at: isoDateTimeSchema
}).strict();
