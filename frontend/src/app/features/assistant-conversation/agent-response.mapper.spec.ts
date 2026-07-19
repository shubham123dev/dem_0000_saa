import { describe, expect, it } from 'vitest';
import { mapAgentRunMessage, summarizeProposalValue } from './agent-response.mapper';

describe('agent response mapper', () => {
  it('maps safe server metadata without exposing proposal ids', () => {
    const mapped=mapAgentRunMessage({id:'m1',sequence:2,role:'assistant',content:'Proposal ready',mode:'action_proposal',answer_source:'deterministic',safe_metadata:{action_proposal:{id:'hidden',action_name:'invite_organization_user',risk_level:'medium',status:'pending_approval',changes:[],expires_at:'2026-07-20T00:00:00Z'},source_count:0,missing_fields:[]},created_at:'2026-07-19T00:00:00Z'});
    expect(mapped.proposal?.actionLabel).toBe('Invite organization user');
    expect(mapped.proposal?.id).toBe('hidden');
  });
  it('summarizes structured values',()=>expect(summarizeProposalValue({secret:'x'})).toBe('Structured value'));
});
