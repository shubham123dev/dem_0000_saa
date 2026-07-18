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

function mapProposal(response: AgentQueryResponse): ConversationProposal | null {
  const proposal = response.action_proposal;
  if (!proposal) return null;
  return {
    actionLabel: humanizeIdentifier(proposal.action_name),
    riskLevel: proposal.risk_level,
    statusLabel: humanizeIdentifier(proposal.status),
    expiresAt: proposal.expires_at,
    changes: proposal.changes.slice(0, 8).map((change) => ({
      fieldLabel: humanizeIdentifier(change.field),
      beforeSummary: summarizeProposalValue(change.before),
      afterSummary: summarizeProposalValue(change.after)
    }))
  };
}

export function mapAgentResponse(
  response: AgentQueryResponse,
  id: string,
  createdAt: string
): ConversationMessage {
  const answer = response.answer.length <= 8000 ? response.answer : `${response.answer.slice(0, 7999)}…`;
  const message = emptyConversationMessage('assistant', answer, id, createdAt);
  return {
    ...message,
    mode: response.mode,
    answerSource: response.answer_source,
    sourceCount: Math.max(response.evidence_ids.length, response.results.length),
    missingFields: response.missing_fields.slice(0, 20).map((field) => humanizeIdentifier(field).slice(0, 160)),
    proposal: mapProposal(response)
  };
}
