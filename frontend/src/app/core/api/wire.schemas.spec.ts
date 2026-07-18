import { describe, expect, it } from 'vitest';
import { agentQueryResponseSchema, errorEnvelopeSchema, workplaceResourceSearchRequestSchema } from './wire.schemas';

describe('wire schemas', () => {
  it('rejects a read response carrying an action proposal', () => {
    const parsed = agentQueryResponseSchema.safeParse({ mode:'read', organization_id:'org', answer:'x', evidence_ids:[], answer_source:'deterministic', results:[], action_proposal:{}, missing_fields:[] });
    expect(parsed.success).toBe(false);
  });
  it('validates the canonical error envelope', () => {
    expect(errorEnvelopeSchema.parse({error:{code:'permission_denied',message:'Denied',request_id:'req_1'}}).error.code).toBe('permission_denied');
  });
  it('applies safe resource-search defaults', () => {
    expect(workplaceResourceSearchRequestSchema.parse({filters:{}})).toEqual({filters:{},sort_by:null,descending:false,limit:50,offset:0});
  });
});
