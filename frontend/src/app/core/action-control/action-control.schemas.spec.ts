import { describe, expect, it } from 'vitest';
import { actionProposalControlSchema } from './action-control.schemas';

describe('action control contracts', () => {
  it('accepts a safe governed proposal projection', () => {
    const parsed=actionProposalControlSchema.parse({id:'p1',action_name:'update_role',action_label:'Update role',resource_label:'Membership',status:'approved',risk_level:'medium',requested_by:'Workspace admin',created_at:'2026-07-19T00:00:00Z',expires_at:'2026-07-19T01:00:00Z',approval_progress:{approved:1,required:1,complete:true},self_approval_allowed:true,required_approver_permission:'agent.actions.approve',changes:[{field:'Role',before:'Reader',after:'Administrator'}],allowed_operations:{approve:false,reject:false,cancel:true,execute:true,reconcile:false,create_rollback:false},source_conversation_id:'c1',execution:null});
    expect(parsed.allowed_operations.execute).toBe(true);
  });
  it('rejects raw extra fields',()=>expect(()=>actionProposalControlSchema.parse({secret:'x'})).toThrow());
});
