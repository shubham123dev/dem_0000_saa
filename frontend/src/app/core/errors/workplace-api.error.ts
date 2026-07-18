export interface WorkplaceErrorView {
  code: string;
  title: string;
  message: string;
  requestId?: string;
  retryable: boolean;
  suggestedAction: 'retry' | 'refresh' | 'request_new_proposal' | 'contact_admin' | 'none';
}

export class WorkplaceApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly requestId?: string,
    readonly causeValue?: unknown
  ) {
    super(message, { cause: causeValue });
    this.name = 'WorkplaceApiError';
  }
}
