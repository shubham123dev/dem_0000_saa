import { HttpErrorResponse, type HttpInterceptorFn } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';
import { WorkplaceApiError } from '../errors/workplace-api.error';
import { errorEnvelopeSchema } from './wire.schemas';

export const apiErrorInterceptor: HttpInterceptorFn = (request, next) => next(request).pipe(
  catchError((error: unknown) => {
    if (error instanceof WorkplaceApiError) return throwError(() => error);
    if (error instanceof HttpErrorResponse) {
      const parsed = errorEnvelopeSchema.safeParse(error.error);
      if (parsed.success) {
        return throwError(() => new WorkplaceApiError(error.status, parsed.data.error.code, parsed.data.error.message, parsed.data.error.request_id, error));
      }
      const requestId = error.headers?.get('X-Request-Id') ?? undefined;
      const message = error.status === 0 ? 'The backend could not be reached.' : 'The server returned an unexpected error response.';
      return throwError(() => new WorkplaceApiError(error.status, 'unexpected_response', message, requestId, error));
    }
    return throwError(() => new WorkplaceApiError(0, 'network_error', 'The request failed before a response was received.', undefined, error));
  })
);
