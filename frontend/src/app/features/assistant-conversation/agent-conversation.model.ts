import { z } from 'zod';

export const conversationProposalChangeSchema = z.object({
  fieldLabel: z.string().min(1).max(160),
  beforeSummary: z.string().max(180),
  afterSummary: z.string().max(180)
}).strict();

export const conversationProposalSchema = z.object({
  actionLabel: z.string().min(1).max(200),
  riskLevel: z.enum(['low', 'medium', 'high']),
  statusLabel: z.string().min(1).max(120),
  expiresAt: z.iso.datetime({ offset: true }),
  changes: z.array(conversationProposalChangeSchema).max(8)
}).strict();

export const conversationMessageSchema = z.object({
  id: z.string().min(1),
  role: z.enum(['user', 'assistant', 'notice', 'error']),
  text: z.string().max(8000),
  createdAt: z.iso.datetime({ offset: true }),
  mode: z.enum(['read', 'action_proposal', 'clarification_required']).nullable(),
  answerSource: z.enum(['model', 'deterministic']).nullable(),
  sourceCount: z.number().int().nonnegative(),
  missingFields: z.array(z.string().min(1).max(160)).max(20),
  proposal: conversationProposalSchema.nullable(),
  tone: z.enum(['info', 'warning', 'danger']).nullable(),
  title: z.string().max(160).nullable(),
  retryable: z.boolean(),
  contextNote: z.string().max(240).nullable()
}).strict();

export const pendingClarificationSchema = z.object({
  originalRequest: z.string().min(1).max(4000),
  collectedDetails: z.array(z.string().min(1).max(1200)).max(8),
  question: z.string().min(1).max(4000),
  missingFields: z.array(z.string().min(1).max(160)).max(20)
}).strict();

export const conversationSnapshotSchema = z.object({
  version: z.literal(1),
  organizationScope: z.string().min(1).max(24),
  messages: z.array(conversationMessageSchema).max(60),
  pendingClarification: pendingClarificationSchema.nullable()
}).strict();

export type ConversationProposal = z.infer<typeof conversationProposalSchema>;
export type ConversationMessage = z.infer<typeof conversationMessageSchema>;
export type PendingClarification = z.infer<typeof pendingClarificationSchema>;
export type ConversationSnapshot = z.infer<typeof conversationSnapshotSchema>;

export function emptyConversationMessage(
  role: ConversationMessage['role'],
  text: string,
  id: string,
  createdAt: string
): ConversationMessage {
  return {
    id,
    role,
    text,
    createdAt,
    mode: null,
    answerSource: null,
    sourceCount: 0,
    missingFields: [],
    proposal: null,
    tone: null,
    title: null,
    retryable: false,
    contextNote: null
  };
}
