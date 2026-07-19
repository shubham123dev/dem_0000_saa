import { expect, type Page, test } from '@playwright/test';

const proposal = {
  id:'proposal_invite_1',action_name:'invite_organization_user',action_label:'Invite organization user',
  resource_label:'Organization membership',status:'pending_approval',risk_level:'medium',
  requested_by:'Workspace administrator',created_at:'2026-07-19T12:00:00Z',expires_at:'2026-07-19T12:15:00Z',
  approval_progress:{approved:0,required:1,complete:false},self_approval_allowed:true,
  required_approver_permission:'agent.actions.approve',
  changes:[{field:'Organization membership',before:'Not set',after:'Invited sandbox reader'}],
  allowed_operations:{approve:true,reject:true,cancel:false,execute:false,reconcile:false,create_rollback:false},
  source_conversation_id:'conversation_action',execution:null
};

async function openAssistant(page:Page){
  const toggle=page.getByRole('button',{name:/Ask AI/}).first();
  const panel=page.getByRole('complementary',{name:'Ask AI'});
  if(!(await panel.isVisible()))await toggle.click();
  await expect(panel).toBeVisible();
  return panel;
}

async function mockProposalRun(page:Page){
  const run={id:'run_action',conversation_id:'conversation_action',status:'queued',current_stage:'request_acceptance',final_mode:null,error_code:null,cancellation_requested_at:null,attempt_count:0,terminal:false,created_at:'2026-07-19T12:00:00Z',started_at:null,completed_at:null};
  const user={id:'message_action_1',sequence:1,role:'user',content:'Invite Demo Analyst',mode:null,answer_source:null,safe_metadata:null,created_at:'2026-07-19T12:00:00Z'};
  const assistant={id:'message_action_2',sequence:2,role:'assistant',content:'The requested change was prepared as a dry-run proposal and requires explicit approval before execution.',mode:'action_proposal',answer_source:'deterministic',safe_metadata:{source_count:0,missing_fields:[],action_proposal:{action_name:'invite_organization_user',risk_level:'medium',status:'pending_approval',changes:[{field:'organization_membership',before:null,after:'invited sandbox_reader'}],expires_at:'2026-07-19T12:15:00Z'}},created_at:'2026-07-19T12:00:02Z'};
  await page.route('**/api/workplace/organizations/**/agent/runs',route=>route.fulfill({status:202,contentType:'application/json',body:JSON.stringify({conversation_id:'conversation_action',run,user_message:user,events_url:'/events',created:true})}));
  await page.route('**/api/workplace/organizations/**/agent/conversations/conversation_action',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({conversation_id:'conversation_action',messages:[user],active_run:run})}));
  await page.route('**/api/workplace/organizations/**/agent/runs/run_action/events**',route=>route.fulfill({status:200,contentType:'text/event-stream',body:`id: 1\nevent: run.accepted\ndata: ${JSON.stringify({schema_version:1,run_id:'run_action',sequence:1,type:'run.accepted',stage:'request_acceptance',message:'Request accepted',payload:null,terminal:false,occurred_at:'2026-07-19T12:00:00Z'})}\n\nid: 2\nevent: proposal.created\ndata: ${JSON.stringify({schema_version:1,run_id:'run_action',sequence:2,type:'proposal.created',stage:'completion',message:'Proposal ready',payload:{message:assistant},terminal:true,occurred_at:'2026-07-19T12:00:02Z'})}\n\n`}));
}

test('right-side proposal uses authoritative state and approval never executes',async({page})=>{
  await mockProposalRun(page);
  let executePosts=0;
  await page.route('**/api/workplace/organizations/**/agent/control/conversations/conversation_action/action',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(proposal)}));
  await page.route('**/api/workplace/organizations/**/agent/control/actions/proposal_invite_1/approve',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({...proposal,status:'approved',approval_progress:{approved:1,required:1,complete:true},allowed_operations:{...proposal.allowed_operations,approve:false,reject:false,cancel:true,execute:true}})}));
  await page.route('**/api/workplace/organizations/**/agent/control/actions/proposal_invite_1/execute',route=>{executePosts+=1;return route.abort();});
  await page.goto('/');
  const panel=await openAssistant(page);
  await panel.getByRole('textbox',{name:'Ask the workplace agent'}).fill('Invite Demo Analyst');
  await panel.getByRole('button',{name:'Send'}).click();
  await expect(panel.getByRole('button',{name:'Approve'})).toBeVisible();
  await expect(panel.getByRole('button',{name:'Reject'})).toBeVisible();
  await panel.getByRole('button',{name:'Approve'}).click();
  await expect(panel.getByRole('dialog',{name:'Confirm proposal decision'})).toBeVisible();
  await panel.getByRole('button',{name:'Confirm approve'}).click();
  await expect(panel.getByText('Status: approved')).toBeVisible();
  await expect(panel.getByRole('button',{name:'Approve'})).toHaveCount(0);
  expect(executePosts).toBe(0);
});

test('medium-risk rejection requires a reason before submission',async({page})=>{
  await mockProposalRun(page);
  let rejectPosts=0;
  await page.route('**/api/workplace/organizations/**/agent/control/conversations/conversation_action/action',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(proposal)}));
  await page.route('**/api/workplace/organizations/**/agent/control/actions/proposal_invite_1/reject',route=>{rejectPosts+=1;return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({...proposal,status:'rejected',allowed_operations:{approve:false,reject:false,cancel:false,execute:false,reconcile:false,create_rollback:false}})});});
  await page.goto('/');
  const panel=await openAssistant(page);
  await panel.getByRole('textbox',{name:'Ask the workplace agent'}).fill('Invite Demo Analyst');
  await panel.getByRole('button',{name:'Send'}).click();
  await panel.getByRole('button',{name:'Reject'}).click();
  await expect(panel.getByRole('button',{name:'Confirm reject'})).toBeDisabled();
  await panel.getByRole('textbox',{name:/Reason/}).fill('Duplicate demonstration account');
  await panel.getByRole('button',{name:'Confirm reject'}).click();
  await expect(panel.getByText('Status: rejected')).toBeVisible();
  expect(rejectPosts).toBe(1);
});
