import { describe, expect, it } from 'vitest';
import { normalizeWorkplaceError } from './error-normalizer';
import { WorkplaceApiError } from './workplace-api.error';

describe('normalizeWorkplaceError', () => {
  it('maps stale proposals to a new-proposal action', () => {
    const view = normalizeWorkplaceError(new WorkplaceApiError(409,'agent_action_stale','State changed','req_1'));
    expect(view.suggestedAction).toBe('request_new_proposal');
    expect(view.requestId).toBe('req_1');
  });
});
