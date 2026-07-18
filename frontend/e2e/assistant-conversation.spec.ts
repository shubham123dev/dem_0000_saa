import { expect, type Page, test } from '@playwright/test';

async function openAssistant(page: Page) {
  const panel=page.getByRole('complementary',{name:'Ask AI'});
  if (await panel.count() === 0) await page.getByRole('button',{name:/Ask AI/}).first().click();
  await expect(panel).toBeVisible();
  return panel;
}

test('submits a real REST query and renders a normalized read answer', async ({page}) => {
  await page.route('**/api/workplace/organizations/**/agent/query', async (route) => {
    const body=route.request().postDataJSON() as {query:string};
    expect(body.query).toBe('List active users');
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({mode:'read',organization_id:'org_sandbox_001',answer:'There are twelve active users.',evidence_ids:['evidence_internal'],answer_source:'model',results:[{tool_name:'internal_tool',data:{count:12}}],action_proposal:null,missing_fields:[]})});
  });
  await page.goto('/');
  const panel=await openAssistant(page);
  const composer=panel.getByRole('textbox',{name:'Ask the workplace agent'});
  await composer.fill('List active users');
  await panel.getByRole('button',{name:'Send'}).click();
  await expect(panel.getByText('There are twelve active users.')).toBeVisible();
  await expect(panel.getByText('1 verified source')).toBeVisible();
  await expect(panel).not.toContainText('evidence_internal');
  await expect(panel).not.toContainText('internal_tool');
  await page.reload();
  await expect((await openAssistant(page)).getByText('There are twelve active users.')).toBeVisible();
});

test('replays clarification context without pretending the backend has conversation memory', async ({page}) => {
  let call=0;
  await page.route('**/api/workplace/organizations/**/agent/query', async (route) => {
    call += 1;
    const body=route.request().postDataJSON() as {query:string};
    if (call === 1) {
      await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({mode:'clarification_required',organization_id:'org_sandbox_001',answer:'Which report should receive access?',evidence_ids:[],answer_source:'deterministic',results:[],action_proposal:null,missing_fields:['report_id']})});
      return;
    }
    expect(body.query).toContain('Original request:');
    expect(body.query).toContain('Additional details from the user:');
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({mode:'read',organization_id:'org_sandbox_001',answer:'The requested report is available for review.',evidence_ids:[],answer_source:'deterministic',results:[],action_proposal:null,missing_fields:[]})});
  });
  await page.goto('/');
  const panel=await openAssistant(page);
  const composer=panel.getByRole('textbox',{name:'Ask the workplace agent'});
  await composer.fill('Grant report access');
  await panel.getByRole('button',{name:'Send'}).click();
  await expect(panel.getByText('More detail is required')).toBeVisible();
  await composer.fill('Use the quarterly market report');
  await panel.getByRole('button',{name:'Send'}).click();
  await expect(panel.getByText('The requested report is available for review.')).toBeVisible();
});

test('renders governed proposal review without executing it', async ({page}) => {
  await page.route('**/api/workplace/organizations/**/agent/query', async (route) => {
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({mode:'action_proposal',organization_id:'org_sandbox_001',answer:'A reviewable onboarding proposal is ready.',evidence_ids:[],answer_source:'deterministic',results:[],missing_fields:[],action_proposal:{id:'proposal_internal',action_name:'onboard_organization_user',risk_level:'medium',status:'pending_approval',changes:[{field:'membership.role',before:null,after:'sandbox_reader'}],expires_at:'2026-07-20T12:00:00Z'}})});
  });
  await page.goto('/');
  const panel=await openAssistant(page);
  await panel.getByRole('textbox',{name:'Ask the workplace agent'}).fill('Onboard a reader');
  await panel.getByRole('button',{name:'Send'}).click();
  await expect(panel.getByText('Review required')).toBeVisible();
  await expect(panel).not.toContainText('proposal_internal');
  await panel.getByRole('button',{name:'Review pending approvals'}).click();
  await expect(page.getByRole('heading',{name:'Pending approvals'})).toBeVisible();
});
