import type { AgentRunMessage } from '../../core/agent-run/agent-run.models';
import type { AgentQueryResponse } from '../../core/api/wire.models';
import type { ConversationMessage, ConversationProposal } from './agent-conversation.model';
import { emptyConversationMessage } from './agent-conversation.model';

const VALUE_LIMIT = 140;

export function humanizeIdentifier(value: string): string {
  const normalized = value.replace(/[._-]+/g, ' ').replace(/\s+/g, ' ').trim();
  if (!normalized) return 'Requested detail';
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

export function summarizeProposalValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return 'Not set';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'number' || typeof value === 'bigint') return String(value);
  if (typeof value === 'string') {
    const compact = value.replace(/\s+/g, ' ').trim();
    return compact.length <= VALUE_LIMIT ? compact : `${compact.slice(0, VALUE_LIMIT - 1)}…`;
  }
  if (Array.isArray(value)) return `${value.length} item${value.length === 1 ? '' : 's'}`;
  return 'Structured value';
}

function mapProposalValue(value: unknown): ConversationProposal | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  const proposal = value as Record<string, unknown>;
  if (
    typeof proposal['action_name'] !== 'string'
    || typeof proposal['expires_at'] !== 'string'
    || !['low','medium','high'].includes(String(proposal['risk_level']))
  ) return null;
  const changes = Array.isArray(proposal['changes']) ? proposal['changes'] : [];
  return {
    id: typeof proposal['id'] === 'string' ? proposal['id'] : null,
    actionLabel: humanizeIdentifier(proposal['action_name']),
    riskLevel: proposal['risk_level'] as 'low' | 'medium' | 'high',
    statusLabel: humanizeIdentifier(typeof proposal['status'] === 'string' ? proposal['status'] : 'pending_approval'),
    expiresAt: proposal['expires_at'],
    changes: changes.slice(0, 8).map((item) => {
      const change = item && typeof item === 'object' && !Array.isArray(item) ? item as Record<string, unknown> : {};
      return {
        fieldLabel: humanizeIdentifier(typeof change['field'] === 'string' ? change['field'] : 'change'),
        beforeSummary: summarizeProposalValue(change['before']),
        afterSummary: summarizeProposalValue(change['after'])
      };
    })
  };
}

function mapProposal(response: AgentQueryResponse): ConversationProposal | null {
  const proposal = response.action_proposal;
  if (!proposal) return null;
  return mapProposalValue(proposal);
}

export function mapAgentResponse(response: AgentQueryResponse, id: string, createdAt: string): ConversationMessage {
  const answer = response.answer.length <= 8000 ? response.answer : `${response.answer.slice(0, 7999)}…`;
  return {
    ...emptyConversationMessage('assistant', answer, id, createdAt),
    mode: response.mode,
    answerSource: response.answer_source,
    sourceCount: Math.max(response.evidence_ids.length, response.results.length),
    missingFields: response.missing_fields.slice(0, 20).map((field) => humanizeIdentifier(field).slice(0, 160)),
    proposal: mapProposal(response)
  };
}

export function mapAgentRunMessage(message: AgentRunMessage): ConversationMessage {
  const metadata = message.safe_metadata ?? {};
  const missing = Array.isArray(metadata['missing_fields']) ? metadata['missing_fields'] : [];
  const sourceCount = typeof metadata['source_count'] === 'number' && Number.isFinite(metadata['source_count']) ? Math.max(0, Math.trunc(metadata['source_count'])) : 0;
  return {
    ...emptyConversationMessage(message.role === 'user' ? 'user' : 'assistant', message.content, message.id, message.created_at),
    mode: message.mode,
    answerSource: message.answer_source,
    sourceCount,
    missingFields: missing.filter((value): value is string => typeof value === 'string').slice(0, 20).map((value) => humanizeIdentifier(value).slice(0, 160)),
    proposal: mapProposalValue(metadata['action_proposal'])
  };
}
