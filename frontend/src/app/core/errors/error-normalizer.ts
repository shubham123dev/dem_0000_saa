import type { WorkplaceErrorView } from './workplace-api.error';
import { WorkplaceApiError } from './workplace-api.error';

const STALE_CODES = new Set(['agent_action_expired', 'agent_action_stale', 'agent_action_cancelled']);
const RETRYABLE_CODES = new Set(['agent_model_request_failed', 'agent_model_unavailable', 'internal_error']);

export function normalizeWorkplaceError(error: unknown): WorkplaceErrorView {
  if (!(error instanceof WorkplaceApiError)) {
    return { code: 'unknown_error', title: 'Something went wrong', message: 'The request could not be completed.', retryable: false, suggestedAction: 'contact_admin' };
  }
  if (STALE_CODES.has(error.code)) {
    return { code: error.code, title: 'Proposal is no longer current', message: error.message, requestId: error.requestId, retryable: false, suggestedAction: 'request_new_proposal' };
  }
  if (error.code === 'permission_denied' || error.code === 'organization_access_denied') {
    return { code: error.code, title: 'Access denied', message: error.message, requestId: error.requestId, retryable: false, suggestedAction: 'contact_admin' };
  }
  const retryable = RETRYABLE_CODES.has(error.code) || error.status === 0 || error.status >= 500;
  return { code: error.code, title: retryable ? 'Service temporarily unavailable' : 'Request could not be completed', message: error.message, requestId: error.requestId, retryable, suggestedAction: retryable ? 'retry' : 'none' };
}
