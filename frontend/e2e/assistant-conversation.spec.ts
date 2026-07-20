import { expect, type Page, test } from '@playwright/test';

async function openAssistant(page: Page) {
  const toggle = page.getByRole('button', { name: /Ask SARA/ }).first();
  const panel = page.getByRole('complementary', { name: 'Ask SARA' });
  await expect(toggle).toBeVisible();
  if (!(await panel.isVisible())) {
    await toggle.click();
  }
  await expect(panel).toBeVisible();
  return panel;
}

const run = { id: 'run_1', conversation_id: 'conversation_1', status: 'queued', current_stage: 'request_acceptance', final_mode: null, error_code: null, cancellation_requested_at: null, attempt_count: 0, terminal: false, created_at: '2026-07-19T00:00:00Z', started_at: null, completed_at: null };
const userMessage = { id: 'message_1', sequence: 1, role: 'user', content: 'List active users', mode: null, answer_source: null, safe_metadata: null, created_at: '2026-07-19T00:00:00Z' };

async function mockRun(page: Page) {
  await page.route('**/api/workplace/organizations/**/agent/runs', route => route.fulfill({ status: 202, contentType: 'application/json', body: JSON.stringify({ conversation_id: 'conversation_1', run, user_message: userMessage, events_url: '/events', created: true }) }));
  await page.route('**/api/workplace/organizations/**/agent/conversations/conversation_1', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ conversation_id: 'conversation_1', messages: [userMessage], active_run: run }) }));
  await page.route('**/api/workplace/organizations/**/agent/runs/run_1/events**', route => route.fulfill({ status: 200, contentType: 'text/event-stream', headers: { 'cache-control': 'no-cache' }, body: [
    'id: 1\nevent: run.accepted\ndata: ' + JSON.stringify({ schema_version: 1, run_id: 'run_1', sequence: 1, type: 'run.accepted', stage: 'request_acceptance', message: 'Request accepted', payload: null, terminal: false, occurred_at: '2026-07-19T00:00:00Z' }) + '\n\n',
    'id: 2\nevent: activity.updated\ndata: ' + JSON.stringify({ schema_version: 1, run_id: 'run_1', sequence: 2, type: 'activity.updated', stage: 'access_check', message: 'Checking your access', payload: null, terminal: false, occurred_at: '2026-07-19T00:00:01Z' }) + '\n\n',
    'id: 3\nevent: answer.completed\ndata: ' + JSON.stringify({ schema_version: 1, run_id: 'run_1', sequence: 3, type: 'answer.completed', stage: 'completion', message: 'Answer ready', payload: { message: { id: 'message_2', sequence: 2, role: 'assistant', content: 'There are twelve active users.', mode: 'read', answer_source: 'deterministic', safe_metadata: { source_count: 1, missing_fields: [] }, created_at: '2026-07-19T00:00:02Z' } }, terminal: true, occurred_at: '2026-07-19T00:00:02Z' }) + '\n\n'
  ].join('') }));
}

test('submits a durable run and renders real SSE activity', async ({ page }) => {
  await mockRun(page);
  await page.goto('/');
  const panel = await openAssistant(page);
  await panel.getByRole('textbox', { name: 'Ask SARA' }).fill('List active users');
  await panel.getByRole('button', { name: 'Send' }).click();
  await expect(panel.getByText('Checking your access')).toBeVisible();
  await expect(panel.getByText('There are twelve active users.')).toBeVisible();
  await expect(panel.getByText('Completed', { exact: true })).toBeVisible();
  await expect(panel.getByText('Working', { exact: true })).toHaveCount(0);
  await expect(panel).not.toContainText('chain-of-thought');
});

test('REST fallback remains supported', async ({ page }) => {
  await page.route('**/config/app-config.json', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ apiBaseUrl: '/api', defaultOrganizationId: 'org_sandbox_001', mockUserId: 'usr_admin_001', requestTimeoutMs: 30000, enableDebugViews: false, streamTransport: 'rest' }) }));
  await page.route('**/api/workplace/organizations/**/agent/query', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ mode: 'read', organization_id: 'org_sandbox_001', answer: 'REST answer.', evidence_ids: [], answer_source: 'deterministic', results: [], action_proposal: null, missing_fields: [] }) }));
  await page.goto('/');
  const panel = await openAssistant(page);
  await panel.getByRole('textbox', { name: 'Ask SARA' }).fill('Status');
  await panel.getByRole('button', { name: 'Send' }).click();
  await expect(panel.getByText('REST answer.')).toBeVisible();
});

test('reconnects from the last sequence without resubmitting the run', async ({ page }) => {
  let postCount = 0;
  let streamCount = 0;
  await page.route('**/api/workplace/organizations/**/agent/runs', (route) => {
    postCount += 1;
    return route.fulfill({ status: 202, contentType: 'application/json', body: JSON.stringify({ conversation_id: 'conversation_1', run, user_message: userMessage, events_url: '/events', created: true }) });
  });
  await page.route('**/api/workplace/organizations/**/agent/conversations/conversation_1', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ conversation_id: 'conversation_1', messages: [userMessage], active_run: run }) }));
  await page.route('**/api/workplace/organizations/**/agent/runs/run_1/events**', (route) => {
    streamCount += 1;
    const event = streamCount === 1
      ? { schema_version: 1, run_id: 'run_1', sequence: 1, type: 'activity.updated', stage: 'access_check', message: 'Checking your access', payload: null, terminal: false, occurred_at: '2026-07-19T00:00:00Z' }
      : { schema_version: 1, run_id: 'run_1', sequence: 2, type: 'answer.completed', stage: 'completion', message: 'Answer ready', payload: { message: { id: 'message_2', sequence: 2, role: 'assistant', content: 'Recovered answer.', mode: 'read', answer_source: 'deterministic', safe_metadata: { source_count: 1, missing_fields: [] }, created_at: '2026-07-19T00:00:02Z' } }, terminal: true, occurred_at: '2026-07-19T00:00:02Z' };
    return route.fulfill({ status: 200, contentType: 'text/event-stream', body: `id: ${event.sequence}\nevent: ${event.type}\ndata: ${JSON.stringify(event)}\n\n` });
  });
  await page.goto('/');
  const panel = await openAssistant(page);
  await panel.getByRole('textbox', { name: 'Ask SARA' }).fill('List active users');
  await panel.getByRole('button', { name: 'Send' }).click();
  await expect(panel.getByText('Recovered answer.')).toBeVisible({ timeout: 10_000 });
  expect(postCount).toBe(1);
  await expect.poll(() => streamCount, { message: 'stream should have been opened at least twice' }).toBeGreaterThanOrEqual(2);
});