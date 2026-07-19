import { expect, test } from '@playwright/test';

const proposal={id:'proposal_1',action_name:'update_organization_member_role',action_label:'Update organization member role',resource_label:'Organization membership',status:'pending_approval',risk_level:'medium',requested_by:'Workspace administrator',created_at:'2026-07-19T00:00:00Z',expires_at:'2026-07-19T01:00:00Z',approval_progress:{approved:0,required:1,complete:false},self_approval_allowed:true,required_approver_permission:'agent.actions.approve',changes:[{field:'Role',before:'Reader',after:'Administrator'}],allowed_operations:{approve:true,reject:true,cancel:false,execute:false,reconcile:false,create_rollback:false},source_conversation_id:'conversation_1',execution:null};

test('reviews, approves, and explicitly executes a governed action',async({page})=>{
 let executionPosts=0;
 await page.route('**/api/workplace/organizations/**/agent/control/actions?**',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({proposals:[proposal],next_cursor:null})}));
 await page.route('**/api/workplace/organizations/**/agent/control/actions',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({proposals:[proposal],next_cursor:null})}));
 await page.route('**/api/workplace/organizations/**/agent/control/actions/proposal_1',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(proposal)}));
 await page.route('**/api/workplace/organizations/**/agent/control/actions/proposal_1/approve',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({...proposal,status:'approved',approval_progress:{approved:1,required:1,complete:true},allowed_operations:{...proposal.allowed_operations,approve:false,reject:false,cancel:true,execute:true}})}));
 await page.route('**/api/workplace/organizations/**/agent/control/actions/proposal_1/execution/events**',route=>route.fulfill({status:200,contentType:'text/event-stream',body:'id: 1\nevent: execution.succeeded\ndata: '+JSON.stringify({schema_version:1,proposal_id:'proposal_1',sequence:1,type:'execution.succeeded',stage:'completion',message:'Execution completed and verified',payload:{outcome:'succeeded'},terminal:true,occurred_at:'2026-07-19T00:00:02Z'})+'\n\n'}));
 await page.route('**/api/workplace/organizations/**/agent/control/actions/proposal_1/execute',route=>{executionPosts+=1;return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({...proposal,status:'succeeded',approval_progress:{approved:1,required:1,complete:true},allowed_operations:{approve:false,reject:false,cancel:false,execute:false,reconcile:false,create_rollback:true},execution:{outcome:'succeeded',resource_label:'Organization membership',before:{Role:'Reader'},after:{Role:'Administrator'},error_code:null,started_at:'2026-07-19T00:00:01Z',completed_at:'2026-07-19T00:00:02Z',executed_by:'Workspace administrator',rollback_available:true}})});});
 await page.goto('/');
 await page.getByRole('button',{name:'Pending approvals',exact:true}).evaluate((el: HTMLElement) => el.click());
 await expect(page.getByRole('heading',{name:'Approval Center'})).toBeVisible();
 await page.getByRole('button',{name:/Update organization member role/}).click();
 await expect(page.getByText('Reader')).toBeVisible();
 await expect(page.locator('.change-row').filter({hasText:'Proposed'}).getByText('Administrator')).toBeVisible();
 await page.getByRole('button',{name:'Approve'}).click();
 await page.getByRole('button',{name:'Confirm approve'}).click();
 await expect(page.getByRole('button',{name:'Execute approved change'})).toBeVisible();
 expect(executionPosts).toBe(0);
 await page.getByRole('button',{name:'Execute approved change'}).click();
 await page.getByRole('button',{name:'Confirm execute'}).click();
 await expect(page.getByText('Execution completed and verified')).toBeVisible();
 expect(executionPosts).toBe(1);
 await expect(page.locator('body')).not.toContainText('proposal_1');
});
