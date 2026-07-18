import { describe, expect, it } from 'vitest';
import type { AgentQueryResponse } from '../../core/api/wire.models';
import { humanizeIdentifier, mapAgentResponse, summarizeProposalValue } from './agent-response.mapper';

describe('agent response mapper', () => {
  it('maps a proposal without exposing proposal or evidence identifiers', () => {
    const response: AgentQueryResponse = {
      mode: 'action_proposal', organization_id: 'org_internal', answer: 'A proposal is ready.', evidence_ids: [], answer_source: 'deterministic', results: [], missing_fields: [],
      action_proposal: { id: 'proposal_internal', action_name: 'onboard_organization_user', risk_level: 'medium', status: 'pending_approval', expires_at: '2026-07-19T12:00:00Z', changes: [{ field: 'membership.role', before: null, after: 'sandbox_reader' }] }
    };
    const mapped = mapAgentResponse(response, 'message-1', '2026-07-19T10:00:00Z');
    expect(mapped.proposal?.actionLabel).toBe('Onboard organization user');
    expect(JSON.stringify(mapped)).not.toContain('proposal_internal');
    expect(JSON.stringify(mapped)).not.toContain('org_internal');
  });

  it('humanizes identifiers and summarizes structured values safely', () => {
    expect(humanizeIdentifier('report_access.status')).toBe('Report access status');
    expect(summarizeProposalValue({ secret: 'value' })).toBe('Structured value');
  });
});
